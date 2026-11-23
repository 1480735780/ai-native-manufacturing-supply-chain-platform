// 计费管理（C++ wms-c5-costmanagement）
import Request from "../request";

/** 去掉空查询条件，避免后端拼接无效 SQL */
export const cleanParams = data => {
	const result = {};
	Object.keys(data || {}).forEach(key => {
		const value = data[key];
		if (value !== "" && value !== null && value !== undefined) {
			result[key] = value;
		}
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

const requestAction = async request => {
	const res = await request();
	if (res.code === 10000) {
		return res.data;
	}
	throw res;
};

const requestBlob = async request => {
	const res = await request();
	return res.data;
};

/* ============================ 费用明细 ============================ */

/** 获取费用明细列表（条件+分页） */
export const listCostDetails = (data, success, fail) =>
	requestList("/cost-management/cost-detail/query-cost", data, success, fail);

/** 录入费用明细 */
export const addCostDetail = data =>
	requestAction(() => Request.requestJson(Request.POST, "/cost-management/cost-detail/add-cost", data));

/** 修改费用明细 */
export const updateCostDetail = data =>
	requestAction(() => Request.requestJson(Request.PUT, "/cost-management/cost-detail/edit-cost", data));

/** 删除费用明细 */
export const deleteCostDetail = id =>
	requestAction(() =>
		Request.requestForm(Request.DELETE, `/cost-management/cost-detail/by-id/${encodeURIComponent(id)}`),
	);

/** 批量删除费用明细 */
export const deleteCostDetails = ids =>
	requestAction(() =>
		Request.requestJson(Request.DELETE, "/cost-management/cost-detail/remove-batch", ids),
	);

/** 批量收款 */
export const chargeCostDetails = ids =>
	requestAction(() => Request.requestJson(Request.PUT, "/cost-management/cost-detail/charge-by-ids", ids));

/** 批量取消收款 */
export const dischargeCostDetails = ids =>
	requestAction(() => Request.requestJson(Request.PUT, "/cost-management/cost-detail/discharge-by-ids", ids));

/** 导出费用明细（按选中 id） */
export const downloadCostDetails = ids =>
	requestBlob(() =>
		Request.requestJson(Request.POST, "/cost-management/cost-detail/download", ids, {
			responseType: "blob",
		}),
	);

/** 导入费用明细 */
export const uploadCostDetails = file =>
	requestAction(() => Request.postFile("/cost-management/cost-detail/upload", { file }));

/** 费用名称列表（复用计费配置） */
export const listCostNames = (data, success, fail) =>
	requestList("/billing-configuration/query-all", data, success, fail);

/* ============================ 费用合计 ============================ */

/** 费用合计列表（条件+分页） */
export const listCostSums = (data, success, fail) =>
	requestList("/cost-management/cost-sum/query-cost-sum", data, success, fail);

/** 导出费用合计 */
export const downloadCostSum = data =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/cost-management/cost-sum/export-data", cleanParams(data), {
			responseType: "blob",
		}),
	);

/* ======================== 已收款费用合计 ======================== */

/** 已收款费用合计列表（条件+分页） */
export const listReceivedFees = (data, success, fail) =>
	requestList(
		"/cost-management/total-amount-of-received-fees/query-list-of-total-fees",
		data,
		success,
		fail,
	);

/** 导出已收款费用合计 */
export const exportReceivedFees = data =>
	requestBlob(() =>
		Request.request(Request.POST, "/cost-management/total-amount-of-received-fees/export", null, undefined, {
			params: cleanParams(data),
			responseType: "blob",
		}),
	);

/* ============================ 客户账单 ============================ */

/** 有账单的客户列表（分页+条件） */
export const listCustomerBills = (data, success, fail) =>
	requestList("/cost-management/customer-bill/query", data, success, fail);

/** 导出未清账单 */
export const exportUnsettledBill = customercode =>
	requestBlob(() =>
		Request.requestForm(
			Request.GET,
			"/cost-management/customer-bill/export-unsettled",
			{ customercode },
			{ responseType: "blob" },
		),
	);

/** 导出期间账单 */
export const exportPeriodBill = data =>
	requestBlob(() =>
		Request.requestForm(
			Request.GET,
			"/cost-management/customer-bill/export-period",
			cleanParams(data),
			{ responseType: "blob" },
		),
	);

/* ============================ 外包卸货费 ============================ */

/** 外包卸货费列表（条件+分页） */
export const listUnloadingFees = (data, success, fail) =>
	requestList("/cost-management/unloading-fee/page-query", data, success, fail);

/** 导出外包卸货费 */
export const downloadUnloadingFees = data =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/cost-management/unloading-fee/download", cleanParams(data), {
			responseType: "blob",
		}),
	);

/* ============================ 外包装车费 ============================ */

/** 外包装车费列表（条件+分页） */
export const listLoadingFees = (data, success, fail) =>
	requestList("/cost-management/loading-fee/page-query", data, success, fail);

/** 导出外包装车费 */
export const downloadLoadingFees = data =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/cost-management/loading-fee/download", cleanParams(data), {
			responseType: "blob",
		}),
	);

/** 保存下载文件 */
export const saveBlob = (blob, filename) => {
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	link.click();
	URL.revokeObjectURL(url);
};
