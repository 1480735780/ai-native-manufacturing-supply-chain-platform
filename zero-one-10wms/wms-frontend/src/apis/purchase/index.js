// 采购管理（j6-stockln）
import Request from "../request";

const requestPurchase = async (request, success, fail) => {
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

/** 收货登记列表 */
export const listGoodReceive = (data, success, fail) =>
	requestPurchase(() => Request.requestForm(Request.GET, "/stock/good-receive/query-all", data), success, fail);

/** 待验收货物列表（批量收货/进货通知明细） */
export const listToAcceptItems = (data, success, fail) =>
	requestPurchase(() => Request.requestForm(Request.GET, "/stock/bulk_receipt/toaccept/items", data), success, fail);

/** 进货通知单列表（预约进货/客户进货/其他入库/入库通知单管理） */
export const listImportNotices = (data, success, fail) =>
	requestPurchase(() => Request.requestForm(Request.GET, "/stock/imNotice-manage/list", data), success, fail);

/** 入库通知单详情 */
export const getImportNoticeDetail = (noticeId, success, fail) =>
	requestPurchase(() => Request.requestForm(Request.GET, `/stock/imNotice-manage/detail/${noticeId}`), success, fail);

/** 录入入库通知单 */
export const insertImportNotice = (data) => Request.requestJson(Request.POST, "/stock/imNotice-manage/insert", data);

/** 修改入库通知单 */
export const updateImportNotice = (data) => Request.requestJson(Request.POST, "/stock/imNotice-manage/update", data);

/** 完成入库通知单 */
export const confirmImportNotice = (noticeId) =>
	Request.requestForm(Request.POST, "/stock/imNotice-manage/confirm", { notice_id: noticeId });

/** 删除入库通知单 */
export const deleteImportNotice = (noticeId) =>
	Request.requestForm(Request.POST, "/stock/imNotice-manage/delete", { noticeId });

/** 上传入库通知单附件 */
export const uploadImportNoticeAttachment = (file) => Request.postFile("/stock/imNotice-manage/upload", { file });

/** 打印：notice=通知单 / goods=货品信息 / inbound=入库单 */
export const printImportNotice = (kind, noticeId) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, `/stock/imNotice-manage/print/${kind}/${noticeId}`, null, {
			responseType: "blob",
		}),
	);

/** 导出：acceptance=验收单 / inbound=入库单 / goods-id=货品ID / tin-label=托盘标签 */
export const exportImportNotice = (kind, noticeId) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, `/stock/imNotice-manage/export/${kind}/${noticeId}`, null, {
			responseType: "blob",
		}),
	);

/** 进货通知明细列表（条件+分页） */
export const listInNoticeItems = (data, success, fail) =>
	requestPurchase(() => Request.requestForm(Request.GET, "/stock/imNotice-detail/items", data), success, fail);

/** 导出进货通知明细 */
export const exportInNoticeItems = (params) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/stock/imNotice-detail/export", params, { responseType: "blob" }),
	);

/** 批量验收 */
export const batchAcceptItems = (items) =>
	Request.requestJson(Request.PUT, "/stock/bulk_receipt/acceptance/items/batch", items);

/** 收货登记详情 */
export const getGoodReceiveDetail = (id, success, fail) =>
	requestPurchase(() => Request.requestForm(Request.GET, `/stock/good-receive/${id}`), success, fail);

/** 录入收货登记 */
export const addGoodReceive = (data) => Request.requestJson(Request.POST, "/stock/good-receive/addItem", data);

/** 修改收货登记 */
export const updateGoodReceive = (data) => Request.requestJson(Request.POST, "/stock/good-receive/modifyItem", data);

/** 删除收货登记 */
export const deleteGoodReceive = (id) => Request.requestForm(Request.DELETE, `/stock/good-receive/${id}`);

/** 批量修改储位 */
export const batchModifyGoodReceiveBin = (data) =>
	Request.requestJson(Request.POST, "/stock/good-receive/batchModifyBin", data);

/** 批量修改生产日期 */
export const batchModifyGoodReceiveProductionDate = (data) =>
	Request.requestJson(Request.POST, "/stock/good-receive/batchModifyProductionDate", data);

/** 上架货物（支持批量） */
export const batchShelfGoodReceive = (data) =>
	Request.requestJson(Request.POST, "/stock/good-receive/batchShelf", data);

/** 导入收货登记 */
export const importGoodReceive = (file) => Request.postFile("/stock/good-receive/importItems", { file });

/** 导出收货登记 */
export const exportGoodReceive = (params) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/stock/good-receive/exportAllItems", params, { responseType: "blob" }),
	);

/** 收货上架：未上架货物列表 */
export const listNotShelvedItems = (data, success, fail) =>
	requestPurchase(() => Request.requestForm(Request.GET, "/stock/not-shelved/query-all", data), success, fail);

/** 收货上架：导出未上架货物 */
export const exportNotShelvedItems = (params) =>
	requestBlob(() => Request.requestForm(Request.GET, "/stock/not-shelved/export", params, { responseType: "blob" }));

/* ============================ 入库通知单下拉数据 ============================ */

const requestOptions = async (request, success) => {
	try {
		const res = await request();
		success(res.data);
	} catch (err) {
		console.warn("下拉数据加载失败", err);
		success(null);
	}
};

/** 订单类型（条件+分页） */
export const listOrderTypeOptions = (success) =>
	requestOptions(
		() => Request.requestForm(Request.GET, "/repository/order-type/query-all", { pageIndex: 1, pageSize: 200 }),
		success,
	);

/** 客户列表（条件+分页） */
export const listCustomerOptions = (success) =>
	requestOptions(
		() => Request.requestForm(Request.GET, "/md/customer/query-all", { pageIndex: 1, pageSize: 500 }),
		success,
	);

/** 供应商列表（条件+分页） */
export const listSupplierOptions = (success) =>
	requestOptions(
		() => Request.requestForm(Request.GET, "/md/provider/query-all", { pageIndex: 1, pageSize: 500 }),
		success,
	);

/** 商品列表（条件+分页） */
export const listGoodsOptions = (success) =>
	requestOptions(
		() => Request.requestForm(Request.GET, "/md/goods/query-all", { pageIndex: 1, pageSize: 500 }),
		success,
	);

/** 月台名称列表 */
export const listPlatformOptions = (success) =>
	requestOptions(() => Request.requestForm(Request.GET, "/platmanag/def/name-list"), success);

/** 仓库名称列表 */
export const listWarehouseOptions = (success) =>
	requestOptions(() => Request.requestForm(Request.GET, "/chuweiguanli/cangkudingyi/query-cangku-name-list"), success);
