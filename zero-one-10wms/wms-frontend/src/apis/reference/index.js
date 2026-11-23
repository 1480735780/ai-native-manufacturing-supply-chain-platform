// 基础资料 / 地区配置（C++ wms-c6-areaconf：/areaconf）
import Request from "../request";

const cleanParams = (data) => {
	const result = {};
	Object.keys(data || {}).forEach((key) => {
		const value = data[key];
		if (value !== "" && value !== null && value !== undefined) result[key] = value;
	});
	return result;
};

const requestList = async (url, data, success, fail) => {
	try {
		const res = await Request.requestForm(Request.GET, url, cleanParams(data));
		if (res.code === 10000) {
			success(res.data);
			return;
		}
		throw res;
	} catch (err) {
		console.warn(err);
		fail && fail();
	}
};

const requestAction = async (request) => {
	const res = await request();
	if (res.code === 10000) return res.data;
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

const timestampName = (prefix) => {
	const d = new Date();
	const pad = (n) => String(n).padStart(2, "0");
	return `${prefix}_${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}.xlsx`;
};

// ==================== 产品属性 / 商品类目 / 品质代码等（保留原有引用） ====================

/** 产品属性列表 */
export const listGoodsTypes = (data, success, fail) =>
	requestList("/pa/list-pa", data, success, fail);

/** 商品类目树 */
export const listGoodsCategories = (success, fail) =>
	requestList("/gc/query-category-tree", {}, success, fail);

/** 品质代码列表 */
export const listQualityCodes = (data, success, fail) =>
	requestList("/qcd/query", data, success, fail);

/** 品检状态列表 */
export const listQualityStatuses = (data, success, fail) =>
	requestList("/pis/list-pis", data, success, fail);

/** 工作状态列表 */
export const listWorkStatuses = (data, success, fail) =>
	requestList("/ops/list-ops", data, success, fail);

/** 在职状态列表 */
export const listEmploymentStatuses = (data, success, fail) =>
	requestList("/es/query", data, success, fail);

/** 学历代码列表 */
export const listEduCodes = (data, success, fail) =>
	requestList("/staffconf/educode/list", data, success, fail);

/** 性别代码列表 */
export const listSexCodes = (data, success, fail) =>
	requestList("/staffconf/sexcode/list", data, success, fail);

// ==================== 工作状态 /ops（C++ wms-c1-persalloc） ====================

/** 录入工作状态 */
export const addWorkStatus = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/ops/add-ops", data));

/** 修改工作状态（body: {id, work_sta_code, work_sta_name}） */
export const modifyWorkStatus = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/ops/modify-ops", data));

/** 删除单条工作状态（query: id） */
export const removeWorkStatus = (id) =>
	requestAction(() => Request.requestForm(Request.DELETE, "/ops/delete", { id }));

/** 批量删除工作状态（body: {ids}） */
export const removeWorkStatusBatch = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/ops/delete-batch", { ids }));

/** 导入工作状态（Excel） */
export const importWorkStatuses = (file) =>
	requestAction(() => Request.postFile("/ops/upload", { file }));

/** 导出工作状态（返回文件流） */
export const exportWorkStatuses = () =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/ops/download", { filename: "work-state.xlsx" }, { responseType: "blob" }),
	);

export const workStatusFileName = () => timestampName("工作状态");

// ==================== 在职状态 /es（C++ wms-c1-persalloc） ====================

/** 录入在职状态 */
export const addEmploymentStatus = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/es/add", data));

/** 修改在职状态（body: {id, pos_sta_code, pos_sta_name}） */
export const modifyEmploymentStatus = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/es/modify", data));

/** 批量删除在职状态（body: {rows: [{code}]}，按业务编码删除） */
export const removeEmploymentStatuses = (codes) =>
	requestAction(() =>
		Request.requestJson(Request.DELETE, "/es/remove-es", { rows: codes.map((code) => ({ code })) }),
	);

/** 导入在职状态（Excel） */
export const importEmploymentStatuses = (file) =>
	requestAction(() => Request.postFile("/es/import", { file }));

/** 导出在职状态（返回文件流） */
export const exportEmploymentStatuses = () =>
	requestBlob(() => Request.requestForm(Request.GET, "/es/export", {}, { responseType: "blob" }));

export const employmentStatusFileName = () => timestampName("在职状态");

// ==================== 学历代码 /staffconf/educode（C++ wms-c6-staffconf） ====================

/** 录入学历代码 */
export const addEduCode = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/staffconf/educode/add", data));

/** 修改学历代码（body: {id, code, name}，注意字段是 code/name 而非 educode/eduname） */
export const modifyEduCode = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/staffconf/educode/modify", data));

/** 删除单条学历代码（query: id） */
export const removeEduCode = (id) =>
	requestAction(() => Request.requestForm(Request.DELETE, "/staffconf/educode/delete", { id }));

/** 批量删除学历代码（body: {ids}） */
export const removeEduCodesBatch = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/staffconf/educode/delete-batch", { ids }));

/** 导入学历代码（Excel） */
export const importEduCodes = (file) =>
	requestAction(() => Request.postFile("/staffconf/educode/import", { file }));

/** 导出学历代码（返回文件流） */
export const exportEduCodes = () =>
	requestBlob(() => Request.requestForm(Request.GET, "/staffconf/educode/export", {}, { responseType: "blob" }));

export const eduCodeFileName = () => timestampName("学历代码");

// ==================== 性别代码 /staffconf/sexcode（C++ wms-c6-staffconf） ====================

/** 录入性别代码 */
export const addSexCode = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/staffconf/sexcode/add", data));

/** 修改性别代码（body: {id, code, name}） */
export const modifySexCode = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/staffconf/sexcode/modify", data));

/** 批量删除性别代码（body: {delList: [id]}） */
export const removeSexCodes = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/staffconf/sexcode/delete", { delList: ids }));

/** 导入性别代码（Excel） */
export const importSexCodes = (file) =>
	requestAction(() => Request.postFile("/staffconf/sexcode/import", { file }));

/** 导出性别代码（返回文件流） */
export const exportSexCodes = () =>
	requestBlob(() => Request.requestForm(Request.GET, "/staffconf/sexcode/export", {}, { responseType: "blob" }));

export const sexCodeFileName = () => timestampName("性别代码");


/** 出库拣货任务（任务确认） */
export const listPickingTasks = (data, success, fail) =>
	requestList("/task-confirm/query-all", data, success, fail);

// ==================== 城市类型 /areaconf/citytype ====================

/** 城市类型列表（条件+分页） */
export const listCityTypes = (data, success, fail) =>
	requestList("/areaconf/citytype/list", data, success, fail);

/** 城市类型名称列表（下拉） */
export const listCityTypeNames = (success, fail) =>
	requestList("/areaconf/citytype/namelist", {}, success, fail);

/** 录入城市类型 */
export const addCityType = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/areaconf/citytype/add", data));

/** 修改城市类型 */
export const updateCityType = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/areaconf/citytype/modify", data));

/** 单条删除城市类型 */
export const removeCityType = (id) =>
	requestAction(() => Request.requestForm(Request.DELETE, "/areaconf/citytype/del", { id }));

/** 批量删除城市类型 */
export const removeCityTypesBatch = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/areaconf/citytype/delete-batch", { ids }));

/** 导入城市类型（Excel） */
export const importCityTypes = (file) =>
	requestAction(() => Request.postFile("/areaconf/citytype/import", { file }));

/** 导出城市类型（返回文件流） */
export const exportCityTypes = () =>
	requestBlob(() => Request.requestForm(Request.GET, "/areaconf/citytype/export", {}, { responseType: "blob" }));

export const cityTypeFileName = () => timestampName("城市类型");

// ==================== 大区信息 /areaconf/bareainfo ====================

/** 大区信息列表（条件+分页） */
export const listBigAreas = (data, success, fail) =>
	requestList("/areaconf/bareainfo/infolist", data, success, fail);

/** 大区信息名称列表（下拉） */
export const listBigAreaNames = (success, fail) =>
	requestList("/areaconf/bareainfo/namelist", {}, success, fail);

/** 录入大区信息 */
export const addBigArea = (data) =>
	requestAction(() =>
		Request.requestJson(Request.POST, "/areaconf/bareainfo/add", {
			region_code: data.code,
			region_name: data.name,
			region_rdata: data.rdata,
		}),
	);

/** 修改大区信息 */
export const updateBigArea = (data) =>
	requestAction(() =>
		Request.requestJson(Request.PUT, "/areaconf/bareainfo/modify", {
			id: data.id,
			region_code: data.code,
			region_name: data.name,
			region_rdata: data.rdata,
		}),
	);

/** 单条删除大区信息（按 code） */
export const removeBigArea = (code) =>
	requestAction(() => Request.requestForm(Request.DELETE, "/areaconf/bareainfo/delete", { code }));

/** 批量删除大区信息 */
export const removeBigAreasBatch = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/areaconf/bareainfo/delete-batch", { ids }));

/** 导入大区信息（Excel） */
export const importBigAreas = (file) =>
	requestAction(() => Request.postFile("/areaconf/bareainfo/import", { file }));

/** 导出大区信息（返回文件流） */
export const exportBigAreas = () =>
	requestBlob(() => Request.requestForm(Request.GET, "/areaconf/bareainfo/export", {}, { responseType: "blob" }));

export const bigAreaFileName = () => timestampName("大区信息");

// ==================== 片区信息 /areaconf/dareainfo ====================

/** 片区信息列表（条件+分页） */
export const listDistrictAreas = (data, success, fail) =>
	requestList("/areaconf/dareainfo/infolist", data, success, fail);

/** 片区信息名称列表（下拉） */
export const listDistrictAreaNames = (success, fail) =>
	requestList("/areaconf/dareainfo/namelist", {}, success, fail);

/** 录入片区信息 */
export const addDistrictArea = (data) =>
	requestAction(() =>
		Request.requestJson(Request.POST, "/areaconf/dareainfo/add", {
			area_code: data.area_code,
			area_name: data.area_name,
		}),
	);

/** 修改片区信息 */
export const updateDistrictArea = (data) =>
	requestAction(() =>
		Request.requestJson(Request.PUT, "/areaconf/dareainfo/modify", {
			id: data.id,
			area_code: data.area_code,
			area_name: data.area_name,
		}),
	);

/** 单条删除片区信息 */
export const removeDistrictArea = (id) =>
	requestAction(() => Request.requestForm(Request.DELETE, `/areaconf/dareainfo/del/${id}`, {}));

/** 批量删除片区信息 */
export const removeDistrictAreasBatch = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/areaconf/dareainfo/delete-batch", { ids }));

/** 导入片区信息（Excel） */
export const importDistrictAreas = (file) =>
	requestAction(() => Request.postFile("/areaconf/dareainfo/import", { file }));

/** 导出片区信息（返回文件流） */
export const exportDistrictAreas = () =>
	requestBlob(() => Request.requestForm(Request.GET, "/areaconf/dareainfo/export", {}, { responseType: "blob" }));

export const districtAreaFileName = () => timestampName("片区信息");

// ==================== 地区信息 /areaconf/areainfo ====================

/** 地区信息列表（条件+分页） */
export const listRegionInfos = (data, success, fail) =>
	requestList("/areaconf/areainfo/get", data, success, fail);

/** 地区信息名称树（左侧树 / 筛选） */
export const listRegionNameTree = (success, fail) =>
	requestList("/areaconf/areainfo/nametree", {}, success, fail);

/** 录入地区信息 */
export const addRegionInfo = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/areaconf/areainfo/add", data));

/** 修改地区信息 */
export const updateRegionInfo = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/areaconf/areainfo/modify", data));

/** 单条删除地区信息（body 为裸 JSON 字符串 id） */
export const removeRegionInfo = (id) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/areaconf/areainfo/delete", id));

/** 批量删除地区信息 */
export const removeRegionInfosBatch = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/areaconf/areainfo/delete-batch", { ids }));

/** 导入地区信息（Excel） */
export const importRegionInfos = (file) =>
	requestAction(() => Request.postFile("/areaconf/areainfo/import", { file }));

/** 导出地区信息（返回文件流） */
export const exportRegionInfos = () =>
	requestBlob(() => Request.requestForm(Request.GET, "/areaconf/areainfo/export", {}, { responseType: "blob" }));

export const regionInfoFileName = () => timestampName("地区信息");
