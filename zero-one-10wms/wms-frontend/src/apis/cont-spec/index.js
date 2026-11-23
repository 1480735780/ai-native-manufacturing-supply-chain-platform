// 其他配置 - 箱规（Java wms-j8-othermana：/othermana/specification）
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

const BASE = "/othermana/specification";

/** 获取箱规列表（条件+分页） */
export const listSpecifications = (data, success, fail) =>
	requestList(`${BASE}/list`, data, success, fail);

/** 获取箱规详情 */
export const getSpecification = (id, success, fail) =>
	requestList(`${BASE}/get-by-id`, { id }, success, fail);

/** 录入箱规 */
export const addSpecification = (data) =>
	requestAction(() => Request.requestJson(Request.POST, `${BASE}/add`, data));

/** 修改箱规 */
export const updateSpecification = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, `${BASE}/modify`, data));

/** 批量删除箱规（body: [{id}]） */
export const removeSpecifications = (ids) =>
	requestAction(() =>
		Request.requestJson(Request.DELETE, `${BASE}/remove-batch`, ids.map((id) => ({ id }))),
	);

/** 导入箱规（Excel） */
export const importSpecifications = (file) =>
	requestAction(() => Request.postFile(`${BASE}/import`, { file }));

/** 导出箱规（返回文件流） */
export const exportSpecifications = () =>
	requestBlob(() =>
		Request.requestForm(Request.GET, `${BASE}/export`, {}, { responseType: "blob" }),
	);
