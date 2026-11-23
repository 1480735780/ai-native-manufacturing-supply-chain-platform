// 企业配置（C++ wms-c2-comconfig）：行业分类 / 企业属性 / 企业状态 / 企业等级 / 公司信息
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
		fail();
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

const saveBlob = (blob, filename) => {
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	link.click();
	URL.revokeObjectURL(url);
};

/* ============================ 行业分类 /indclas ============================ */
export const listIndustryClasses = (data, success, fail) =>
	requestList("/indclas/get-indclaslist", data, success, fail);
export const listIndustryClassNames = (data, success, fail) =>
	requestList("/indclas/get-indclasnamelist", data, success, fail);
export const addIndustryClass = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/indclas/add-indclas", data));
export const modifyIndustryClass = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/indclas/modify-indclas", data));
export const removeIndustryClasses = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/indclas/delete-indclas", { Id: ids }));
export const downloadIndustryClasses = (filename) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/indclas/download-indclas", { filename }, { responseType: "blob" }),
	);
export const uploadIndustryClasses = (file) => requestAction(() => Request.postFile("/indclas/upload-file", { file }));
export { saveBlob };

/* ============================ 企业属性 /entattr ============================ */
export const listCompanyAttributes = (data, success, fail) =>
	requestList("/entattr/get-entattrnamelist", data, success, fail);
export const listCompanyAttributeNames = (data, success, fail) =>
	requestList("/entattr/get-entattrname", data, success, fail);
export const addCompanyAttribute = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/entattr/add-entattr", data));
export const modifyCompanyAttribute = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/entattr/mod-entattr", data));
export const removeCompanyAttributes = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/entattr/delete-entattr", { ids }));
export const downloadCompanyAttributes = (filename) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/entattr/download-entattr", { filename }, { responseType: "blob" }),
	);
export const uploadCompanyAttributes = (file) =>
	requestAction(() => Request.postFile("/entattr/upload-entattr", { file }));

/* ============================ 企业状态 /entstat /comstate ============================ */
export const listCompanyStatuses = (data, success, fail) =>
	requestList("/entstat/get-entstatlist", data, success, fail);
export const listCompanyStatusForList = (success, fail) =>
	requestList("/entstat/get-entstatforlist", null, success, fail);
export const addCompanyStatus = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/comstate/add-state", data));
export const modifyCompanyStatus = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/comstate/modify-state", data));
export const removeCompanyStatus = (id, ids) =>
	requestAction(() =>
		Request.requestJson(Request.DELETE, `/comstate/remove-state/${encodeURIComponent(id)}`, { companyId: ids }),
	);
export const downloadCompanyStatuses = (filename) =>
	requestBlob(() => Request.requestForm(Request.GET, "/entstat/download-file", { filename }, { responseType: "blob" }));
// 后端已改为 multipart 文件直传，与其他模块导入模式一致
export const uploadCompanyStatuses = (file) => requestAction(() => Request.postFile("/entstat/upload-file", { file }));

/* ============================ 企业等级 /entlevel /entleve ============================ */
export const listCompanyLevels = (data, success, fail) =>
	requestList("/entlevel/get-entlevellist", data, success, fail);
export const listCompanyLevelNames = (data, success, fail) => requestList("/entleve/level-name", data, success, fail);
export const addCompanyLevel = (data) =>
	requestAction(() => Request.requestJson(Request.POST, "/entattr/add-entlevel", data));
export const modifyCompanyLevel = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/entleve/update-entleve", data));
export const removeCompanyLevels = (ids) =>
	requestAction(() => Request.requestJson(Request.DELETE, "/entleve/delete-entleve", { companyId: ids }));
export const downloadCompanyLevels = () =>
	requestBlob(() => Request.requestForm(Request.GET, "/entleve/export-entleve", null, { responseType: "blob" }));
export const uploadCompanyLevels = (file) => requestAction(() => Request.postFile("/entleve/upload-file", { file }));

/* ============================ 公司信息 /cominfo ============================ */
export const listCompanies = (data, success, fail) => requestList("/cominfo/get-cominfolist", data, success, fail);
export const getCompanyDetail = (id) =>
	requestAction(() => Request.requestForm(Request.GET, "/cominfo/get-cominfodetail", { id }));
export const addCompany = (data) => requestAction(() => Request.requestJson(Request.POST, "/cominfo/add-info", data));
export const modifyCompany = (data) =>
	requestAction(() => Request.requestJson(Request.PUT, "/cominfo/modify-info", data));
export const removeCompany = (id, ids) =>
	requestAction(() =>
		Request.requestJson(Request.DELETE, `/cominfo/remove-info/${encodeURIComponent(id)}`, { companyId: ids }),
	);
export const downloadCompanies = (filename) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/cominfo/download-cominfo", { filename }, { responseType: "blob" }),
	);
export const uploadCompanies = (file) => requestAction(() => Request.postFile("/cominfo/upload-cominfo", { file }));

export const exportBlob = saveBlob;
