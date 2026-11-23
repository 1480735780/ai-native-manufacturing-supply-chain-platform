// 每日检查（j3-daycheck）
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

const requestDayCheckList = async (url, data, success, fail) => {
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

/** 导出接口返回 201，需要兼容全局拦截器只放行 200 的情况 */
const requestBlob = async request => {
	try {
		const res = await request();
		return res.data;
	} catch (err) {
		if (err && err.status === 201 && err.data) {
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

/* ============================ 收货未上架 ============================ */

/** 获取未上架货物列表（条件+分页） */
export const listReceivedUnsold = (data, success, fail) =>
	requestDayCheckList("/daycheck/no-up/get-no-up-goods", data, success, fail);

/** 导出未上架货物 */
export const exportReceivedUnsold = () =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/daycheck/no-up/download", null, { responseType: "blob" }),
	);

/* ============================ 出货异常 ============================ */

/** 获取异常出货列表（条件+分页） */
export const listAbnormalShipment = (data, success, fail) =>
	requestDayCheckList("/daycheck/yi-chang/get-yichang-down", data, success, fail);

/** 导出异常出货 */
export const exportAbnormalShipment = () =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/daycheck/yi-chang/download", null, { responseType: "blob" }),
	);

/* ============================ 温度维护 ============================ */

/** 获取温度列表（分页） */
export const listTemperature = (data, success, fail) =>
	requestDayCheckList("/daycheck/temperature/query", data, success, fail);

/** 录入温度 */
export const addTemperature = data =>
	Request.requestJson(Request.POST, "/daycheck/temperature/add", data);

/** 修改温度 */
export const updateTemperature = data =>
	Request.requestJson(Request.PUT, "/daycheck/temperature/update", data);

/** 删除温度（支持批量） */
export const deleteTemperature = ids =>
	Request.requestForm(Request.DELETE, "/daycheck/temperature/delete", { ids: ids.join(",") });

/** 导入温度 */
export const importTemperature = file =>
	Request.postFile("/daycheck/temperature/import", { file });

/** 导出温度 */
export const exportTemperature = () =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/daycheck/temperature/export", null, { responseType: "blob" }),
	);

/* ========================= 进货延时示警 ========================= */

/** 获取延时货物列表（分页） */
export const listShipmentDelay = (data, success, fail) =>
	requestDayCheckList("/daycheck/delay/im-delay", data, success, fail);

/** 导出延时货物 */
export const exportShipmentDelay = () =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/daycheck/delay/download", null, { responseType: "blob" }),
	);
