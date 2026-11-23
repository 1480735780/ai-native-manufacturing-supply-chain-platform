// 其他配置 - 商品品牌（Java wms-j8-othermana：/othermana/goodsbrand）
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

const BASE = "/othermana/goodsbrand";

/** 获取商品品牌名称列表（下拉框用） */
export const listGoodsBrandNames = (success, fail) =>
	requestList(`${BASE}/name-list`, {}, success, fail);

/** 获取商品品牌列表（条件+分页） */
export const listGoodsBrands = (data, success, fail) =>
	requestList(`${BASE}/query-goodsbrand`, data, success, fail);

/** 录入商品品牌（含图片上传） */
export const addGoodsBrand = (data) =>
	requestAction(() => Request.postFile(`${BASE}/add-goodsbrand`, data));

/** 修改商品品牌回填 */
export const getGoodsBrandForEdit = (id, success, fail) =>
	requestList(`${BASE}/modifybutton`, { id }, success, fail);

/** 提交商品品牌修改（图片可选） */
export const updateGoodsBrand = (data) =>
	requestAction(() => Request.postFile(`${BASE}/modify-goodsbrand`, data));

/** 删除商品品牌（支持批量） */
export const removeGoodsBrands = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, `${BASE}/remove-goodsbrand-by-ids`, ids));

/** 导出商品品牌（按条件全量导出，返回文件流） */
export const exportGoodsBrands = (data) =>
	requestBlob(() =>
		Request.requestJson(Request.POST, `${BASE}/export-goodsbrand`, data, { responseType: "blob" }),
	);

/** 导入商品品牌（Excel 文件上传） */
export const importGoodsBrands = (file) =>
	requestAction(() => Request.postFile(`${BASE}/import-goodsbrand`, { file }));
