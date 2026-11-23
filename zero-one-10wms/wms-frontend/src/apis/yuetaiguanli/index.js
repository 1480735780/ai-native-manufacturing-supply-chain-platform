// 月台管理：月台定义 / 月台计划 / PLC指令
import Request from "../request";

const requestPlat = async (request, success, fail) => {
	try {
		const res = await request();
		if (res.data) {
			success(res.data);
			return;
		}
		fail();
	} catch (err) {
		console.warn(err);
		fail();
	}
};

// ============================================================
// 月台定义（C++ wms-c8-platmanag 服务，前缀 /platmanag/def）
// ============================================================

/** 月台定义-获取名称列表（下拉） */
export const listPlatformNames = (success, fail) =>
	requestPlat(() => Request.requestForm(Request.GET, "/platmanag/def/name-list"), success, fail);

/** 月台定义-条件分页列表 */
export const listPlatform = (data, success, fail) =>
	requestPlat(() => Request.requestForm(Request.GET, "/platmanag/def/list", data), success, fail);

/** 月台定义-录入 */
export const addPlatform = (data, success, fail) =>
	requestPlat(() => Request.requestJson(Request.POST, "/platmanag/def", data), success, fail);

/** 月台定义-修改 */
export const updatePlatform = (data, success, fail) =>
	requestPlat(() => Request.requestForm(Request.PUT, "/platmanag/def", data), success, fail);

/** 月台定义-单条删除 */
export const deletePlatform = (id, success, fail) =>
	requestPlat(() => Request.requestForm(Request.DELETE, `/platmanag/def/${id}`), success, fail);

/** 月台定义-批量删除（逻辑删除） */
export const batchDeletePlatform = (ids, success, fail) =>
	requestPlat(() => Request.requestJson(Request.DELETE, "/platmanag/def/batch", { ids }), success, fail);

/** 月台定义-导出（返回下载地址） */
export const exportPlatform = (success, fail) =>
	requestPlat(() => Request.requestJson(Request.POST, "/platmanag/def/output"), success, fail);

/** 月台定义-导入（Excel 上传） */
export const importPlatform = (file, success, fail) => {
	const formData = new FormData();
	formData.append("file", file);
	return requestPlat(() => Request.request(Request.POST, "/platmanag/def/import", formData, "form"), success, fail);
};

// ============================================================
// PLC 指令（C++ wms-c8-platmanag 服务，前缀 /platmanag/plc）
// ============================================================

/** PLC-条件分页列表 */
export const listPlc = (data, success, fail) =>
	requestPlat(() => Request.requestForm(Request.GET, "/platmanag/plc", data), success, fail);

/** PLC-详情 */
export const getPlcDetail = (id, success, fail) =>
	requestPlat(() => Request.requestForm(Request.GET, "/platmanag/plc/query-by-id", { id }), success, fail);

/** PLC-录入 */
export const addPlc = (data, success, fail) =>
	requestPlat(() => Request.requestJson(Request.POST, "/platmanag/plc", data), success, fail);

/** PLC-修改 */
export const updatePlc = (data, success, fail) =>
	requestPlat(() => Request.requestJson(Request.PUT, "/platmanag/plc", data), success, fail);

/** PLC-单条删除 */
export const deletePlc = (id, success, fail) =>
	requestPlat(() => Request.requestForm(Request.DELETE, `/platmanag/plc/${id}`), success, fail);

/** PLC-批量删除 */
export const batchDeletePlc = (ids, success, fail) =>
	requestPlat(() => Request.requestJson(Request.DELETE, "/platmanag/plc/batch", { ids }), success, fail);

/** PLC-导出（返回下载地址） */
export const exportPlc = (params, success, fail) =>
	requestPlat(() => Request.requestForm(Request.GET, "/platmanag/plc/export", params), success, fail);

/** PLC-导入（Excel 上传） */
export const importPlc = (file, success, fail) => {
	const formData = new FormData();
	formData.append("file", file);
	return requestPlat(() => Request.request(Request.POST, "/platmanag/plc/import", formData, "form"), success, fail);
};

/** PLC-执行指令（支持批量） */
export const executePlc = (ids, success, fail) =>
	requestPlat(() => Request.requestJson(Request.POST, "/platmanag/plc/execute", { ids }), success, fail);

// ============================================================
// 月台计划（Java wms-j7-outgoodsmanage 服务，前缀 /plat-io）
// ============================================================

/** 月台计划-条件分页列表 */
export const listPlatIo = (data, success, fail) =>
	requestPlat(() => Request.requestForm(Request.GET, "/plat-io/list", data), success, fail);

/** 月台计划-录入 */
export const addPlatIo = (data, success, fail) =>
	requestPlat(() => Request.requestJson(Request.POST, "/plat-io", data), success, fail);

/** 月台计划-修改 */
export const updatePlatIo = (data, success, fail) =>
	requestPlat(() => Request.requestJson(Request.PUT, "/plat-io", data), success, fail);
