// 仓库配置（wms-c7-reposity / wms-c8-wconfig）9 个子模块接口
import Request from "../request";

const cleanParams = data => {
	const result = {};
	Object.keys(data || {}).forEach(key => {
		const value = data[key];
		if (value !== "" && value !== null && value !== undefined) {
			result[key] = value;
		}
	});
	return result;
};

/** 列表查询统一封装：成功回调 data，失败回调 */
const requestList = async (url, data, success, fail) => {
	try {
		const res = await Request.requestForm(Request.GET, url, cleanParams(data));
		if (res.data !== undefined && res.data !== null) {
			success(res.data);
			return;
		}
		throw res;
	} catch (err) {
		console.warn(err);
		fail(err);
	}
};

/** 写操作统一封装：成功(code===0) resolve data，失败 reject */
const requestAction = async request => {
	const res = await request();
	if (res.data && res.code === 0) return res.data;
	throw res;
};

/** 导出接口可能返回 201，需要兼容全局拦截器只放行 200 的情况 */
const requestBlob = async request => {
	try {
		const res = await request();
		return res.data;
	} catch (err) {
		if (err && (err.status === 201 || err.status === 200) && err.data) {
			return err.data;
		}
		throw err;
	}
};

/** 保存下载文件 */
export const saveBlob = (blob, filename) => {
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	link.click();
	URL.revokeObjectURL(url);
};

/* ============================ 订单类型 ============================ */

/** 获取订单类型列表（条件+分页） */
export const listOrderTypes = (data, success, fail) =>
	requestList("/repository/order-type/query-all", data, success, fail);

/** 获取订单类型名称列表 */
export const listOrderTypeNames = (data, success, fail) =>
	requestList("/repository/order-type/query-name", data, success, fail);

/** 录入订单类型 */
export const addOrderType = data =>
	requestAction(() => Request.requestJson(Request.POST, "/repository/order-type/add-data", data));

/** 修改订单类型 */
export const updateOrderType = data =>
	requestAction(() => Request.requestJson(Request.PUT, "/repository/ord/modify", data));

/** 删除订单类型 */
export const deleteOrderType = id =>
	requestAction(() => Request.requestForm(Request.DELETE, `/repository/ord-delete/${id}`));

/** 批量删除订单类型（ids: 逗号分隔字符串） */
export const deleteOrderTypeBatch = ids =>
	requestAction(() => Request.requestForm(Request.DELETE, `/repository/ord-delete-batch/${ids}`));

/** 导入订单类型 */
export const importOrderType = file =>
	Request.postFile("/repository/ordertypefile/upload", { file });

/** 导出订单类型 */
export const exportOrderType = filename =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/repository/ordertypefile/download", { filename }, { responseType: "blob" }),
	);

/* ============================ 业务类型 ============================ */

/** 获取业务类型列表（条件+分页） */
export const listBussTypes = (data, success, fail) =>
	requestList("/repository/busstype-query", data, success, fail);

/** 录入业务类型 */
export const addBussType = data =>
	requestAction(() => Request.requestJson(Request.POST, "/repository/busstype-add", data));

/** 修改业务类型 */
export const updateBussType = data =>
	requestAction(() => Request.requestJson(Request.PUT, "/repository/busstype-modify", data));

/** 删除业务类型（单个） */
export const deleteBussType = id =>
	requestAction(() => Request.requestForm(Request.DELETE, `/repository/bussty-del-one/${id}`));

/** 批量删除业务类型 */
export const deleteBussTypeBatch = ids =>
	requestAction(() => Request.requestJson(Request.DELETE, "/repository/bussty-del-part/id", ids));

/** 导入业务类型 */
export const importBussType = file =>
	Request.postFile("/repository/bussty-upload", { file });

/** 导出业务类型 */
export const exportBussType = filename =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/repository/bussty-download", { filename }, { responseType: "blob" }),
	);

/* ============================ 作业类型 ============================ */

/** 获取作业类型列表（条件+分页） */
export const listActTypes = (data, success, fail) =>
	requestList("/repository/queryall-baacttype", data, success, fail);

/** 获取作业类型名称列表（act_type 一套） */
export const listActTypeNames = (data, success, fail) =>
	requestList("/repository/queryall-acttype", data, success, fail);

/** 录入作业类型 */
export const addActType = data =>
	requestAction(() => Request.requestJson(Request.POST, "/repository/adddata-acttype", data));

/** 修改作业类型 */
export const updateActType = data =>
	requestAction(() => Request.requestJson(Request.PUT, "/repository/modify-baacttype", data));

/** 删除作业类型 */
export const deleteActType = id =>
	requestAction(() => Request.requestForm(Request.DELETE, `/repository/delete-baacttype/${id}`));

/** 批量删除作业类型（ids: 逗号分隔字符串） */
export const deleteActTypeBatch = ids =>
	requestAction(() => Request.requestForm(Request.DELETE, `/repository/delete-baacttype-batch/${ids}`));

/** 导入作业类型 */
export const importActType = file =>
	Request.postFile("/repository/upload-baacttypefile", { file });

/** 导出作业类型 */
export const exportActType = filename =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/repository/download-baacttypefile", { filename }, { responseType: "blob" }),
	);

/* ============================ 业务环节 ============================ */

/** 获取业务环节列表（条件+分页） */
export const listBusinessLinks = (data, success, fail) =>
	requestList("/repository/queryall-business-link", data, success, fail);

/** 获取业务环节名称列表 */
export const listBusinessLinkNames = (data, success, fail) =>
	requestList("/repository/getnamelist-business-link", data, success, fail);

/** 录入业务环节 */
export const addBusinessLink = data =>
	requestAction(() => Request.requestJson(Request.POST, "/repository/add-business-link", data));

/** 修改业务环节（后端 DTO 字段名为 ID） */
export const updateBusinessLink = data =>
	requestAction(() =>
		Request.requestJson(Request.PUT, "/repository/operstep/modify", { ...data, ID: data.ID ?? data.id }),
	);

/** 删除业务环节（ids: 逗号分隔字符串） */
export const deleteBusinessLink = ids =>
	requestAction(() => Request.requestJson(Request.DELETE, "/OperStep/delete", { ids }));

/** 导入业务环节 */
export const importBusinessLink = file =>
	Request.postFile("/repository/operstep/uploadexcel", { file });

/** 导出业务环节 */
export const exportBusinessLink = filename =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/repository/operstep/exportexcel", { filename }, { responseType: "blob" }),
	);

/* ============================ 操作类型（wms-c8-wconfig） ============================ */

/** 获取操作类型列表（条件+分页） */
export const listOperationTypes = (data, success, fail) =>
	requestList("/wconfig/operation-type", data, success, fail);

/** 录入操作类型 */
export const addOperationType = data =>
	requestAction(() => Request.requestJson(Request.POST, "/wconfig/operation-type", data));

/** 修改操作类型 */
export const updateOperationType = data =>
	requestAction(() => Request.requestJson(Request.PUT, "/wconfig/operation-type", data));

/** 删除操作类型 */
export const deleteOperationType = id =>
	requestAction(() => Request.requestForm(Request.DELETE, `/wconfig/operation-type/${id}`));

/** 批量删除操作类型（ids: 字符串数组） */
export const deleteOperationTypeBatch = ids =>
	requestAction(() =>
		Request.requestJson(Request.DELETE, "/wconfig/operation-type/batch-delete", { ids }),
	);

/** 导入操作类型 */
export const importOperationType = file =>
	Request.postFile("/wconfig/operation-type/import", { file });

/** 导出操作类型 */
export const exportOperationType = filename =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/wconfig/operation-type/export", { filename }, { responseType: "blob" }),
	);

/* ============================ 提货方式（wms-c8-wconfig） ============================ */

/** 获取提货方式列表（条件+分页） */
export const listLadMods = (data, success, fail) =>
	requestList("/wconfig/ladmod", data, success, fail);

/** 录入提货方式 */
export const addLadMod = data =>
	requestAction(() => Request.requestJson(Request.POST, "/wconfig/ladmod", data));

/** 修改提货方式 */
export const updateLadMod = data =>
	requestAction(() => Request.requestJson(Request.PUT, "/wconfig/ladmod", data));

/** 删除提货方式 */
export const deleteLadMod = id =>
	requestAction(() => Request.requestForm(Request.DELETE, `/wconfig/ladmod/delete?id=${id}`));

/** 批量删除提货方式（ids: 数字数组） */
export const deleteLadModBatch = ids =>
	requestAction(() =>
		Request.requestJson(Request.DELETE, "/wconfig/ladmod/batch-delete", { ids }),
	);

/** 导入提货方式 */
export const importLadMod = file =>
	Request.postFile("/wconfig/ladmod/import", { file });

/** 导出提货方式 */
export const exportLadMod = () =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/wconfig/ladmod/export", null, { responseType: "blob" }),
	);

/* ============================ 接货方式（wms-c8-wconfig） ============================ */

/** 获取接货方式列表（条件+分页） */
export const listRecvGWays = (data, success, fail) =>
	requestList("/wconfig/recv-g-way", data, success, fail);

/** 录入接货方式 */
export const addRecvGWay = data =>
	requestAction(() => Request.requestJson(Request.POST, "/wconfig/recv-g-way", data));

/** 修改接货方式 */
export const updateRecvGWay = data =>
	requestAction(() => Request.requestJson(Request.PUT, "/wconfig/recv-g-way", data));

/** 删除接货方式 */
export const deleteRecvGWay = id =>
	requestAction(() => Request.requestForm(Request.DELETE, `/wconfig/recv-g-way/${id}`));

/** 批量删除接货方式（ids: 字符串数组） */
export const deleteRecvGWayBatch = ids =>
	requestAction(() =>
		Request.requestJson(Request.DELETE, "/wconfig/recv-g-way/batch-delete", { ids }),
	);

/** 导入接货方式 */
export const importRecvGWay = file =>
	Request.postFile("/wconfig/recv-g-way-file/upload_f", { file });

/** 导出接货方式 */
export const exportRecvGWay = filename =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/wconfig/recv-g-way-file/download_f", { filename }, { responseType: "blob" }),
	);

/* ============================ 库位类型 ============================ */

/** 获取库位类型列表（条件+分页） */
export const listLibraries = (data, success, fail) =>
	requestList("/repository/library/query-all", data, success, fail);

/** 获取库位类型名称列表 */
export const listLibraryNames = (data, success, fail) =>
	requestList("/repository/library/query-name", data, success, fail);

/** 录入库位类型 */
export const addLibrary = data =>
	requestAction(() => Request.requestJson(Request.POST, "/repository/library/add", data));

/** 修改库位类型 */
export const updateLibrary = data =>
	requestAction(() => Request.requestJson(Request.PUT, "/repository/library/modify", data));

/** 删除库位类型 */
export const deleteLibrary = id =>
	requestAction(() => Request.requestForm(Request.DELETE, `/repository/library/${id}`));

/** 导入库位类型 */
export const importLibrary = file =>
	Request.postFile("/repository/libraryfile/upload", { file });

/** 导出库位类型 */
export const exportLibrary = filename =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/repository/libraryfile/download", { filename }, { responseType: "blob" }),
	);

/* ============================ 温度属性 ============================ */

/** 获取温度属性列表（条件+分页） */
export const listTemperatures = (data, success, fail) =>
	requestList("/repository/temperature/queryall", data, success, fail);

/** 获取温度属性名称列表 */
export const listTemperatureNames = (data, success, fail) =>
	requestList("/repository/temperature/queryname", data, success, fail);

/** 录入温度属性 */
export const addTemperature = data =>
	requestAction(() => Request.requestJson(Request.POST, "/repository/temperature/add", data));

/** 修改温度属性 */
export const updateTemperature = data =>
	requestAction(() => Request.requestJson(Request.PUT, "/repository/temperature/modify", data));

/** 删除温度属性 */
export const deleteTemperature = id =>
	requestAction(() => Request.requestForm(Request.DELETE, `/repository/temperature/remove?id=${id}`));

/** 导入温度属性 */
export const importTemperature = file =>
	Request.postFile("/repository/temperature/uploadexcel", { file });

/** 导出温度属性 */
export const exportTemperature = filename =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/repository/temperature/downloadexcel", { filename }, { responseType: "blob" }),
	);
