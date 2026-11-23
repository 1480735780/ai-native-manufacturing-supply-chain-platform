// 计费配置模块 API 层
// 后端服务：
//   wms-c4-billingconfig (8105) 费用名称 / 费用类型
//   wms-c5-costconfig    (8108) 计费方式 / 客户计费属性 / 计费商品分类 / 客户计费方式
//                              计量类型 / 价格类型 / 费用模板 / 仓储费率
// 统一经网关 /billing-configuration/**、/cost-config/**、/cost-type/**、/rm/**、/rm_more/** 转发
import Request from "../request";

/**
 * 调用并返回后端 data 字段。
 * 响应拦截器已把 `{ code, message, data }` 原样向下传递，这里再解一层。
 * 注意：不能仅凭存在 `code` 字段判断是否为包装体——部分字典 DTO 本身就有 code 字段。
 */
const call = async (request) => {
	const res = await request();
	if (res && typeof res === "object" && !Array.isArray(res) && "code" in res && "message" in res) {
		return res.data;
	}
	return res;
};

/** 提取分页数据：兼容 C++ PageDTO（data/rows/total）与数组 */
export const pickPage = (payload) => {
	if (!payload) return { rows: [], total: 0 };
	if (Array.isArray(payload)) return { rows: payload, total: payload.length };
	const rows = payload.rows ?? payload.data ?? [];
	const total = payload.total ?? rows.length;
	return { rows, total };
};

/** 下载二进制并触发浏览器保存 */
const saveBlob = (blob, filename) => {
	const url = window.URL.createObjectURL(new Blob([blob]));
	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
	window.URL.revokeObjectURL(url);
};

/* ------------------------------------------------------------------
 * 一、通用字典模块工厂
 * 适用于后端统一约定的 7 个接口：
 *   GET    /cost-config/{module}/query-{module}-page
 *   GET    /cost-config/{module}/query-{module}-name
 *   POST   /cost-config/{module}/add-{module}
 *   PUT    /cost-config/{module}/modify-{module}
 *   DELETE /cost-config/{module}/delete-{module}   body: ["id1","id2"]
 *   GET    /cost-config/{module}/export-{module}   (xlsx)
 *   POST   /cost-config/{module}/import-{module}   multipart file
 * ------------------------------------------------------------------ */
export const createDictApi = (module) => {
	const base = `/cost-config/${module}`;

	/** 分页查询 */
	const page = (params) => call(() => Request.requestForm(Request.GET, `${base}/query-${module}-page`, params));

	/** 名称下拉列表 */
	const nameList = (params) => call(() => Request.requestForm(Request.GET, `${base}/query-${module}-name`, params));

	/** 新增 */
	const add = (data) => call(() => Request.requestJson(Request.POST, `${base}/add-${module}`, data));

	/** 修改 */
	const modify = (data) => call(() => Request.requestJson(Request.PUT, `${base}/modify-${module}`, data));

	/** 批量删除 */
	const remove = (ids) => call(() => Request.requestJson(Request.DELETE, `${base}/delete-${module}`, ids));

	/** 导出 Excel */
	const exportExcel = async (filename) => {
		const res = await Request.requestForm(
			Request.GET,
			`${base}/export-${module}`,
			{},
			{ responseType: "blob" },
		);
		saveBlob(res.data, filename || `${module}.xlsx`);
	};

	/** 导入 Excel */
	const importExcel = (file) => call(() => Request.postFile(`${base}/import-${module}`, { file }));

	return { page, nameList, add, modify, remove, exportExcel, importExcel };
};

/** 计费商品分类（ba_goods_class） */
export const goodsClassApi = createDictApi("goods-class");
/** 客户计费方式（ba_kehuzhuangtai） */
export const customerBillingWayApi = createDictApi("customer-billing-way");
/** 计量类型（ba_pronut_type） */
export const measurementTypeApi = createDictApi("measurement-type");
/** 价格类型（ba_price_type） */
export const priceTypeApi = createDictApi("price-type");
/** 费用模板（ba_cost_conf） */
export const costTemplateApi = createDictApi("cost-template");
/** 仓储费率（wm_cost_conf） */
export const storageRateApi = createDictApi("storage-rate");

/* ------------------------------------------------------------------
 * 二、费用名称（wms-c4-billingconfig）
 * ------------------------------------------------------------------ */
export const listCostNamePage = (params) =>
	call(() => Request.requestForm(Request.GET, "/billing-configuration/query-by-page", params));

export const listCostNameAll = (params) =>
	call(() => Request.requestForm(Request.GET, "/billing-configuration/query-all", params));

export const addCostName = (data) =>
	call(() => Request.requestJson(Request.POST, "/billing-configuration/add-cost-name", data));

export const modifyCostName = (data) =>
	call(() => Request.requestJson(Request.PUT, "/billing-configuration/modify-cost-name", data));

/** 批量删除：后端路径占位 {id} 不参与逻辑，实际取 body.dtoList */
export const removeCostNames = (ids) =>
	call(() =>
		Request.requestJson(Request.DELETE, `/billing-name/batch-delete/${ids[0] ?? 0}`, {
			dtoList: ids.map((id) => ({ id })),
		}),
	);

export const exportCostName = async () => {
	const res = await Request.requestForm(
		Request.GET,
		"/billing-name/download",
		{},
		{ responseType: "blob" },
	);
	saveBlob(res.data, "cost-name.xlsx");
};

export const importCostName = (file) => call(() => Request.postFile("/billing-name/upload", { file }));

/* ------------------------------------------------------------------
 * 三、费用类型（wms-c4-billingtype + wms-c4-billingconfig 删除）
 * ------------------------------------------------------------------ */
export const listCostTypeAll = (params) => call(() => Request.requestForm(Request.GET, "/cost-type/all", params));

export const getCostType = (data) => call(() => Request.requestJson(Request.POST, "/cost-type/gettype", data));

/** 费用类型录入（后端命名为 gettype，实际为新增） */
export const addCostType = getCostType;

/** 费用类型修改 */
export const modifyCostType = (data) =>
	call(() => Request.requestJson(Request.PUT, "/cost-type/modify", data));

/** 费用类型导入 */
export const importCostType = (file) => call(() => Request.postFile("/expense/upload", { file }));

export const exportCostType = async () => {
	const res = await Request.requestForm(Request.GET, "/expense/download", {}, { responseType: "blob" });
	saveBlob(res.data, "cost-type.xlsx");
};

export const removeCostType = (id) => call(() => Request.requestJson(Request.DELETE, `/rm/${id}`, {}));

export const removeCostTypes = (ids) =>
	call(() => Request.requestJson(Request.DELETE, `/rm_more/${ids.join(",")}`, {}));

/* ------------------------------------------------------------------
 * 四、计费方式（wms-c5-costconfig cost-method）
 * ------------------------------------------------------------------ */
export const listCostMethod = (params) =>
	call(() => Request.requestForm(Request.GET, "/cost-config/cost-method/query", params));

export const listCostMethodAll = (params) =>
	call(() => Request.requestForm(Request.GET, "/cost-config/cost-method/query-all", params));

export const addCostMethod = (data) =>
	call(() => Request.requestJson(Request.POST, "/cost-config/cost-method/add", data));

export const modifyCostMethod = (data) =>
	call(() => Request.requestJson(Request.PUT, "/cost-config/cost-method/modify", data));

/** 计费方式批量删除（复用 cost-way 控制器，操作同一张 ba_pronut_method） */
export const removeCostMethods = (ids) =>
	call(() => Request.requestJson(Request.DELETE, "/cost-config/cost-way/delete-way", ids));

/** 计费方式导出 */
export const exportCostMethods = async () => {
	const res = await Request.requestForm(
		Request.GET,
		"/cost-config/cost-way/excel-download",
		{ filename: "cost-method.xlsx" },
		{ responseType: "blob" },
	);
	saveBlob(res.data, "cost-method.xlsx");
};

/** 计费方式导入 */
export const importCostMethods = (file) =>
	call(() => Request.postFile("/cost-config/cost-way/excel-upload", { file }));

/** 仓储费率详细信息 */
export const getStorageRateDetail = (id) =>
	call(() => Request.requestForm(Request.GET, "/cost-config/storage-rate/query-storage-rate-detail", { id }));

/* ------------------------------------------------------------------
 * 五、客户计费属性（wms-c5-costconfig cost-attribute）
 * ------------------------------------------------------------------ */
export const listCostAttributePage = (params) =>
	call(() => Request.requestForm(Request.GET, "/cost-config/query-cost-attribute-page", params));

export const listCostAttributeName = (params) =>
	call(() => Request.requestForm(Request.GET, "/cost-config/query-cost-attribute-name", params));

export const addCostAttribute = (data) =>
	call(() => Request.requestJson(Request.POST, "/cost-config/add-cost-attribute", data));

export const modifyCostAttribute = (data) =>
	call(() => Request.requestJson(Request.PUT, "/cost-config/update-cost-attribute", data));

export const removeCostAttribute = (ids) =>
	call(() => Request.requestJson(Request.DELETE, "/cost-config/cost-attribute/delete-attribute", ids));

export const exportCostAttribute = async () => {
	const res = await Request.requestForm(
		Request.GET,
		"/cost-config/cost-attribute/export-attribute",
		{},
		{ responseType: "blob" },
	);
	saveBlob(res.data, "cost-attribute.xlsx");
};

export const importCostAttribute = (file) =>
	call(() => Request.postFile("/cost-config/cost-attribute/import-attribute", { file }));

/* ------------------------------------------------------------------
 * 六、兼容旧调用（保持既有引用不报错）
 * ------------------------------------------------------------------ */
export const listBillingCosts = (data, success, fail) =>
	listCostNameAll(data)
		.then((res) => success(res))
		.catch((err) => fail(err));

export const listCostTypes = (data, success, fail) =>
	listCostTypeAll(data)
		.then((res) => success(res))
		.catch((err) => fail(err));
