// 其他配置 - 港口信息（Java wms-j8-othermana：/othermana/port）
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
		// 港口列表接口为 POST + JSON body
		const res = await Request.requestJson(Request.POST, url, cleanParams(data));
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

const BASE = "/othermana/port";

/** 获取港口信息列表（条件+分页） */
export const listPorts = (data, success, fail) =>
	requestList(`${BASE}/queryPort`, data, success, fail);

/** 录入港口信息 */
export const addPort = (data) =>
	requestAction(() => Request.requestJson(Request.POST, `${BASE}/addPort`, data));

/** 修改港口信息 */
export const updatePort = (data) =>
	requestAction(() => Request.requestJson(Request.POST, `${BASE}/modifyPort`, data));

/** 删除单个港口信息 */
export const removePort = (id) =>
	requestAction(() => Request.requestForm(Request.POST, `${BASE}/removePort`, { id }));

/** 批量删除港口信息 */
export const removePorts = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, `${BASE}/removePorts`, ids));

/** 导入港口信息（Excel） */
export const importPorts = (file) =>
	requestAction(() => Request.postFile(`${BASE}/uploadPort`, { file }));

/** 导出港口信息（返回文件流） */
export const exportPorts = () =>
	requestBlob(() => Request.requestForm(Request.GET, `${BASE}/exportPort`, {}, { responseType: "blob" }));
