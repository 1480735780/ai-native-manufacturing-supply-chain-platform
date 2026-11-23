// 出库管理（j7-outgoodsmanage）
import Request from "../request";

const requestOut = async (request, success, fail) => {
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

const requestBlob = async (request) => {
	try {
		const res = await request();
		return res.data;
	} catch (err) {
		// 兼容后端返回 200 但全局拦截器走 reject 的情况
		if (err && err.status === 200 && err.data) {
			return err.data;
		}
		throw err;
	}
};

/** 保存浏览器文件 */
export const saveBlob = (blob, filename) => {
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	link.click();
	URL.revokeObjectURL(url);
};

/** 新窗口预览 PDF，被浏览器拦截时自动下载 */
export const previewBlob = (blob, filename) => {
	const url = URL.createObjectURL(blob);
	const win = window.open(url, "_blank");
	if (!win) {
		URL.revokeObjectURL(url);
		saveBlob(blob, filename);
		return;
	}
	setTimeout(() => URL.revokeObjectURL(url), 60_000);
};

/* ============================ 出库通知单 ============================ */

/** 出库通知单列表（条件+分页） */
export const listOutNotices = (data, success, fail) =>
	requestOut(() => Request.requestForm(Request.GET, "/out-goods-manager/query-out-notice-list", data), success, fail);

/** 出库通知单详情 */
export const getOutNoticeDetail = (omNoticeId, success, fail) =>
	requestOut(
		() => Request.requestForm(Request.GET, "/out-goods-manager/query-out-notice-item", { omNoticeId }),
		success,
		fail,
	);

/** 录入出库通知单 */
export const addOutNotice = (data) =>
	Request.requestJson(Request.POST, "/out-goods-manager/add-out-goods-notice", data);

/** 修改出库通知单 */
export const updateOutNotice = (data) =>
	Request.requestJson(Request.PUT, "/out-goods-manager/modify-query", data);

/** 删除出库通知单 */
export const deleteOutNotice = (id) =>
	Request.requestForm(Request.POST, "/out-goods-manager/remove", { id });

/** 上传出库通知单附件 */
export const uploadOutNoticeAttachment = (omNoticeId, file) =>
	Request.postFile("/out-goods-manager/add-upload-fu-jan/", { upFile: file, omNoticeId });

/** 打印拣货单 */
export const printPickingList = (id) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/out-goods-manager/query-picking-list", { id }, {
			responseType: "blob",
		}),
	);

/** 打印出库单 */
export const printOutGoodsList = (id) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/out-goods-manager/query-out-goods-list", { id }, {
			responseType: "blob",
		}),
	);

/** 导出出货通知 */
export const exportOutNoticeH = (params) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/out-goods-manager/export-h", params, { responseType: "blob" }),
	);

/** 导出出库单 */
export const exportOutNoticeI = (params) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/out-goods-manager/export-i", params, { responseType: "blob" }),
	);

/* ============================ 出库明细 ============================ */

/** 出库明细列表（条件+分页） */
export const listOutDetails = (data, success, fail) =>
	requestOut(() => Request.requestForm(Request.GET, "/out-detail/query-all", data), success, fail);

/** 导出出库明细 */
export const exportOutDetails = (params) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/out-detail/export-excel", params, { responseType: "blob" }),
	);

/* ============================ 任务确认 ============================ */

/** 出库任务列表（条件+分页） */
export const listOutboundTasks = (data, success, fail) =>
	requestOut(() => Request.requestForm(Request.GET, "/task-confirm/query-all", data), success, fail);

/** 修改任务 */
export const modifyOutboundTask = (data) =>
	Request.requestJson(Request.POST, "/task-confirm/modify-task", data);

/** 批量设置接收人 */
export const batchSetTaskRecipients = (ids, receiverName) =>
	Request.requestForm(Request.POST, "/task-confirm/batch-confirmation", { ids, receiverName });

/** 批量确认任务 */
export const confirmOutboundTasks = (ids) =>
	Request.requestForm(Request.POST, "/task-confirm/confirm-task", { ids });

/** 生成波次（ids 逗号分隔） */
export const generateOutboundWave = (ids) =>
	Request.requestJson(Request.POST, "/task-confirm/wave", { ids: ids.join(",") });

/** 删除任务（ids 逗号分隔） */
export const deleteOutboundTasks = (ids) =>
	Request.requestJson(Request.POST, "/task-confirm/del", { ids: ids.join(",") });

/** 请求异步导出任务（后端通过 MQ + WebSocket 推送文件地址） */
export const requestTaskExport = () => Request.requestForm(Request.GET, "/task-confirm/export");

/* ============================ 按单拣货 ============================ */

/** 拣货列表（条件+分页） */
export const listAdPick = (data, success, fail) =>
	requestOut(() => Request.requestForm(Request.GET, "/adpick/query-all", data), success, fail);

/** 拣货详情 */
export const getAdPickDetail = (id, success, fail) =>
	requestOut(() => Request.requestForm(Request.GET, "/adpick/query-one", { id }), success, fail);

/** 修改拣货 */
export const modifyAdPick = (data) => Request.requestJson(Request.POST, "/adpick/modify", data);

/** 批量修改拣货 */
export const modifyAdPickList = (list) => Request.requestJson(Request.POST, "/adpick/modify-list", list);

/** 导出拣货数据 */
export const exportAdPick = (queries) =>
	requestBlob(() =>
		Request.requestJson(Request.POST, "/adpick/export-excel", queries, { responseType: "blob" }),
	);

/* ============================ 装车复核 ============================ */

/** 装车复核列表（条件+分页） */
export const listLoadChecks = (data, success, fail) =>
	requestOut(() => Request.requestForm(Request.GET, "/zc-check/query-all", data), success, fail);

/** 批量复核（提交 id、复核数量、通知单号） */
export const batchCheckLoad = (list) => Request.requestJson(Request.POST, "/zc-check/batch-check", list);

/** 一键复核 */
export const oneClickReview = (omNoticeIds) =>
	Request.requestJson(Request.POST, "/zc-check/modify-review-by-list", { omNoticeIds });

/* ============================ 下架管理 ============================ */

/** 下架货物列表（条件+分页） */
export const listDownGoods = (data, success, fail) =>
	requestOut(
		() => Request.requestForm(Request.GET, "/outgoodsmanage/wm-to-down-goods/list", data),
		success,
		fail,
	);

/** 下架货物详情 */
export const getDownGoods = (id, success, fail) =>
	requestOut(() => Request.requestForm(Request.GET, `/outgoodsmanage/wm-to-down-goods/${id}`), success, fail);

/** 修改下架货物 */
export const modifyDownGoods = (data) =>
	Request.requestJson(Request.PUT, "/outgoodsmanage/wm-to-down-goods/modify", data);

/** 批量修改下架数量 */
export const batchUpdateDownGoods = (list) =>
	Request.requestJson(Request.POST, "/outgoodsmanage/wm-to-down-goods/batch-update-down-goods", list);

/** 下架（支持批量） */
export const downGoods = (ids) =>
	Request.requestJson(Request.POST, "/outgoodsmanage/wm-to-down-goods/down-goods", ids);

/** 删除下架任务 */
export const deleteDownGoods = (id) =>
	Request.requestForm(Request.GET, "/outgoodsmanage/wm-to-down-goods/delete-down-goods", { id });

/** 导出下架数据 */
export const exportDownGoods = (ids) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/outgoodsmanage/wm-to-down-goods/export-down-goods-data", {
			ids: ids.join(","),
		}, { responseType: "blob" }),
	);

/* ============================ 异常出库 ============================ */

/** 异常出库列表（条件+分页） */
export const listYcOutbound = (data, success, fail) =>
	requestOut(() => Request.requestForm(Request.GET, "/yc-outbound/query-all", data), success, fail);

/** 导出异常出库 */
export const exportYcOutbound = () =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/yc-outbound/export-excel", null, { responseType: "blob" }),
	);
