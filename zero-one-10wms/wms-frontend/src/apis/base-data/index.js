// 基础资料（wms-java/wms-j5-basezl）API 封装
// 统一约定：列表 GET + form 参数；写操作 JSON；导入 multipart；导出 blob
import Request from "../request";

/** 去掉空查询条件，避免后端拼出无效条件 */
export const cleanParams = (data) => {
	const result = {};
	Object.keys(data || {}).forEach((key) => {
		const value = data[key];
		if (value !== "" && value !== null && value !== undefined) result[key] = value;
	});
	return result;
};

/** 数组参数转逗号分隔，兼容 Spring @RequestParam List；空数组返回 undefined 以免拼出 ids= 触发类型转换异常 */
const joinIds = (ids) => {
	if (ids === null || ids === undefined) return undefined;
	if (Array.isArray(ids)) return ids.length > 0 ? ids.join(",") : undefined;
	return ids;
};

const requestList = async (url, data, success, fail) => {
	try {
		const res = await Request.requestForm(Request.GET, url, cleanParams(data));
		if (res && res.code === 10000) {
			success(res.data);
			return;
		}
		throw res;
	} catch (err) {
		console.warn("[base-data] list failed:", url, err);
		fail && fail(err);
	}
};

const requestAction = async (request) => {
	const res = await request();
	if (res && res.code === 10000) return res.data;
	throw res;
};

const requestBlob = async (request) => {
	const res = await request();
	return res.data;
};

export const saveBlob = (blob, filename) => {
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	link.click();
	URL.revokeObjectURL(url);
};

/* ============================ 客户 /md/customer ============================ */

export const listCustomers = (data, success, fail) =>
	requestList("/md/customer/query-all", data, success, fail);

export const getCustomerDetail = (customerId, success, fail) =>
	requestList("/md/customer/query-one", { customerId }, success, fail);

export const addCustomer = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/md/customer/add-customer", data));

export const updateCustomer = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/md/customer/modify-customer", data));

export const removeCustomers = (ids) =>
	requestAction(() =>
		Request.requestForm(Request.DELETE, "/md/customer/remove-customer", { ids: joinIds(ids) }),
	);

export const exportCustomers = (ids, query = {}) =>
	requestBlob(() =>
		Request.requestForm(
			Request.GET,
			"/md/customer/download",
			{ ...cleanParams(query), ids: joinIds(ids) },
			{ responseType: "blob" },
		),
	);

export const importCustomers = (file) =>
	requestAction(() => Request.postFile("/md/customer/upload", { file }));

/** 客户名称列表（对象结构：id/keHuBianMa/zhongWenQch） */
export const listCustomerNames = (success, fail) =>
	requestList("/md/customer/customer-name-list", {}, success, fail);

/* ======================== 第三方客户 /md/cus-other ======================== */

export const listCusOthers = (data, success, fail) =>
	requestList("/md/cus-other/query-all", data, success, fail);

export const getCusOtherDetail = (keHuBianMa, success, fail) =>
	requestList("/md/cus-other/query-one", { keHuBianMa }, success, fail);

export const addCusOther = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/md/cus-other/add-cus", data));

export const updateCusOther = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/md/cus-other/modify-cus", data));

export const removeCusOthers = (ids) =>
	requestAction(() =>
		Request.requestForm(Request.DELETE, "/md/cus-other/remove-cus", { ids: joinIds(ids) }),
	);

export const exportCusOthers = (ids, query = {}) =>
	requestBlob(() =>
		Request.requestForm(
			Request.GET,
			"/md/cus-other/export",
			{ ...cleanParams(query), ids: joinIds(ids) },
			{ responseType: "blob" },
		),
	);

export const importCusOthers = (file) =>
	requestAction(() => Request.postFile("/md/cus-other/upload", { file }));

/* ============================ 供应商 /md/provider ============================ */

export const listProviders = (data, success, fail) =>
	requestList("/md/provider/query-all", data, success, fail);

export const getProviderDetail = (id, success, fail) =>
	requestList("/md/provider/get-details-provider", { id }, success, fail);

export const addProvider = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/md/provider/add-provider", data));

export const updateProvider = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/md/provider/change-provider", data));

export const removeProviders = (providerIds) =>
	requestAction(() =>
		Request.requestForm(Request.DELETE, "/md/provider/delete-provider", {
			providerIds: joinIds(providerIds),
		}),
	);

export const exportProviders = (providerIds, query = {}) =>
	requestBlob(() =>
		Request.requestForm(
			Request.GET,
			"/md/provider/export",
			{ ...cleanParams(query), providerIds: joinIds(providerIds) },
			{ responseType: "blob" },
		),
	);

export const importProviders = (file) =>
	requestAction(() => Request.postFile("/md/provider/upload", { file }));

/* ============================== 商品 /md/goods ============================== */

export const listGoods = (data, success, fail) =>
	requestList("/md/goods/query-all", data, success, fail);

export const getGoodsDetail = (shpBianMa, success, fail) =>
	requestList("/md/goods/query-one", { shp_bian_ma: shpBianMa }, success, fail);

export const addGoods = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/md/goods/add-goods", data));

export const updateGoods = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/md/goods/update-goods", data));

/** 商品删除：后端接收 body JSON 数组 */
export const removeGoods = (shpBianMas) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/md/goods/delete-goods", shpBianMas || []));

export const exportGoods = (shpBianMas, query = {}) =>
	requestBlob(() =>
		Request.requestForm(
			Request.GET,
			"/md/goods/download",
			{ ...cleanParams(query), shpBianMas: joinIds(shpBianMas) },
			{ responseType: "blob" },
		),
	);

export const importGoods = (file) =>
	requestAction(() => Request.postFile("/md/goods/upload", { file }));

/** 打印标签：返回 PDF blob */
export const printGoodsLabel = (shpBianMa) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/md/goods/print", { shpBianMa }, { responseType: "blob" }),
	);

/* =============================== RFID /md/rfid =============================== */

export const listRfids = (data, success, fail) =>
	requestList("/md/rfid/query-all", data, success, fail);

export const getRfidDetail = (rfid, success, fail) =>
	requestList("/md/rfid/query-one", { rfid }, success, fail);

export const addRfid = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/md/rfid/add-rfid", data));

export const updateRfid = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/md/rfid/modify-rfid", data));

export const removeRfids = (rfidList) =>
	requestAction(() =>
		Request.requestForm(Request.DELETE, "/md/rfid/delete-rfid", { rfidList: joinIds(rfidList) }),
	);

export const exportRfids = (ids, query = {}) =>
	requestBlob(() =>
		Request.requestForm(
			Request.GET,
			"/md/rfid/export",
			{ ...cleanParams(query), ids: joinIds(ids) },
			{ responseType: "blob" },
		),
	);

export const importRfids = (file) =>
	requestAction(() => Request.postFile("/md/rfid/upload", { file }));

/* ====================== 关联模块下拉 / 树（跨模块） ====================== */

/** 行业分类名称列表（c2-comconfig） */
export const listIndustryClassNames = (success, fail) =>
	requestList("/indclas/get-indclasnamelist", {}, success, fail);

/** 企业属性名称列表（c2-comconfig） */
export const listEnterpriseAttrNames = (success, fail) =>
	requestList("/entattr/get-entattrnamelist", {}, success, fail);

/** 企业状态列表（c2-comconfig） */
export const listEnterpriseStatusNames = (success, fail) =>
	requestList("/entstat/get-entstatforlist", {}, success, fail);

/** 企业等级名称列表（c2-comconfig） */
export const listEnterpriseLevelNames = (success, fail) =>
	requestList("/entleve/level-name", {}, success, fail);

/** 商品品牌名称列表（j8-othermana） */
export const listGoodsBrandNames = (success, fail) =>
	requestList("/othermana/goodsbrand/name-list", {}, success, fail);

/** 商品类目名称树（c1-bconf） */
export const getGoodsCategoryTree = (success, fail) =>
	requestList("/gc/query-category-tree", {}, success, fail);

/** 计量单位名称列表（j4-baseConfig） */
export const listMeasurementUnitNames = (success, fail) =>
	requestList("/measurementunit/getnamelist", {}, success, fail);

/* ============================ 兼容旧调用名 ============================ */

export const getshangpingApi = listGoods;
export const getGoodsDetailApi = listGoods;
export const getCustomerApi = listCustomers;
export const getProviderApi = listProviders;
export const getRfidApi = listRfids;
export const getCusOtherApi = listCusOthers;

/* ============================ 消息模块（保持原样） ============================ */

export const addMessageTemplateAPI = (obj) => {
	return Request.request(Request.POST, "/msgmw/add-messageTemplate", obj, 1);
};

export const updateMessageTemplateAPI = (obj) => {
	return Request.request(Request.PUT, "/msgmw/update-messageTemplate", obj, 1);
};

export const deleteMessageTemplateAPI = (obj) => {
	return Request.request(Request.DELETE, "/msgmw/delete-messageTemplate", obj, 1);
};

export const getMessageCenterAPI = (obj) => {
	return Request.request(Request.GET, "/msgmw/messages", obj, 1);
};

export const updateMessageCenterAPI = (obj, id) => {
	return Request.request(Request.PUT, `/msgmw/messages/${id}`, obj, 1);
};

export const getWorkSettingAPI = (obj) => {
	return Request.request(Request.POST, "/msgmw/query", obj, 1);
};

export const addWorkSettingAPI = (obj) => {
	return Request.request(Request.POST, "/msgmw/add", obj, 1);
};

export const updateWorkSettingAPI = (obj) => {
	return Request.request(Request.PUT, "/msgmw/update", obj, 1);
};

export const deleteWorkSettingAPI = (obj) => {
	return Request.request(Request.DELETE, "/msgmw/delete", obj, 1);
};

export const getSqlListAPI = (obj) => {
	return Request.request(Request.GET, "/msgmw/query-sql-list", obj, 1);
};

export const addSqlAPI = (obj) => {
	return Request.request(Request.POST, "/msgmw/add-sql", obj, 1);
};

export const updateSqlAPI = (obj) => {
	return Request.request(Request.PUT, "/msgmw/modify-sql", obj, 1);
};

export const deleteSqlAPI = (obj) => {
	return Request.request(Request.DELETE, "/msgmw/remove-sql", obj, 1);
};
