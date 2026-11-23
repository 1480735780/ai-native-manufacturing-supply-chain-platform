// 其他配置 - 箱型（Java wms-j8-othermana：/contshape）
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

const BASE = "/contshape";

/** 获取箱型列表（条件+分页） */
export const listContTypes = (data, success, fail) =>
	requestList(`${BASE}/queryAll`, data, success, fail);

/** 获取箱型详情 */
export const getContType = (id, success, fail) =>
	requestList(`${BASE}/query/${id}`, {}, success, fail);

/** 录入箱型 */
export const addContType = (data) =>
	requestAction(() => Request.requestJson(Request.POST, `${BASE}/add`, data));

/** 修改箱型 */
export const updateContType = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, `${BASE}/modify`, data));

/** 批量删除箱型（query 参数 ids，逗号分隔） */
export const removeContTypes = (ids) =>
	requestAction(() => Request.requestForm(Request.DELETE, `${BASE}/delete`, { ids: ids.join(",") }));

/** 导入箱型（Excel） */
export const importContTypes = (file) =>
	requestAction(() => Request.postFile(`${BASE}/import`, { file }));

/** 导出箱型（返回文件流） */
export const exportContTypes = () =>
	requestBlob(() => Request.requestForm(Request.GET, `${BASE}/export`, {}, { responseType: "blob" }));
