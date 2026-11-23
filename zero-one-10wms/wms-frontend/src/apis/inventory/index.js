// 盘点管理 / 仓储配置（C++ wms-c4-icmanagement / wms-c7-reposity）
import Request from "../request";

const requestInv = async (request, success, fail) => {
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

/**
 * 写操作统一封装：成功(code===0) resolve data，失败 reject
 * C++ JsonVO 的成功码是 0（RS_SUCCESS 无自定义码）
 */
const requestInvAction = async (request) => {
	const res = await request();
	if (res.data && res.code === 0) return res.data;
	throw res;
};

/** 导出接口可能返回 201，需要兼容全局拦截器只放行 200 的情况 */
const requestBlob = async (request) => {
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

/* ============================ 列表查询（已有） ============================ */

/** 盘点列表 */
export const listCheck = (data, success, fail) =>
	requestInv(() => Request.requestForm(Request.GET, "/inv/check", data), success, fail);

/** 双人报价列表 */
export const listReviewStt = (data, success, fail) =>
	requestInv(() => Request.requestForm(Request.GET, "/review/query-all", data), success, fail);

/** 综合盘点列表 */
export const listOverallInventory = (data, success, fail) =>
	requestInv(() => Request.requestForm(Request.GET, "/overall-inventory/query", data), success, fail);

/** 移库（动碰盘）列表 */
export const listSttOnMove = (data, success, fail) =>
	requestInv(() => Request.requestForm(Request.GET, "/stt/stt-on-move", data), success, fail);

/** 移库盘点列表 */
export const listMovingBin = (data, success, fail) =>
	requestInv(
		() => Request.requestForm(Request.GET, "/moving-warehouse-inventory/query", data),
		success,
		fail,
	);

/** 下架调整列表 */
export const listRemovalAdjust = (data, success, fail) =>
	requestInv(() => Request.requestForm(Request.GET, "/removal-adjustment/query", data), success, fail);

/** 上架调整（调整单）列表 */
export const listUpAdjust = (data, success, fail) =>
	requestInv(() => Request.requestForm(Request.GET, "/lis/qurry", data), success, fail);

/** 盘点差异过账列表 */
export const listGoodsDiffPost = (data, success, fail) =>
	requestInv(() => Request.requestForm(Request.GET, "/goods/query-all", data), success, fail);

/** 订单类型列表 */
export const listOrderTypes = (data, success, fail) =>
	requestInv(
		() => Request.requestForm(Request.GET, "/repository/order-type/query-all", data),
		success,
		fail,
	);

/* ============================ 盘点任务生成（批量） ============================ */

/** 综合盘点：批量生成盘点任务（body: { ids: [...] }） */
export const createOverallTasks = (ids) =>
	requestInvAction(() => Request.requestJson(Request.POST, "/overall-inventory/create", { ids }));

/** 动碰盘点：批量生成盘点任务（body: { ids: [...] }） */
export const createSttOnMoveTasks = (ids) =>
	requestInvAction(() => Request.requestJson(Request.POST, "/stt/stt-on-move", { ids }));

/* ============================ 盘点任务编辑 / 删除 ============================ */

/** 编辑盘点任务（PUT /overall-inventory/modify，id 必填其余可选） */
export const updateCheckTask = (data) =>
	requestInvAction(() => Request.requestJson(Request.PUT, "/overall-inventory/modify", data));

/** 删除盘点任务（逻辑删除：stt_sta 置为已删除） */
export const deleteSttTask = (id) =>
	requestInvAction(() => Request.requestJson(Request.DELETE, `/stt/stt-task/${id}`));

/* ============================ 复盘 / 差异过账 ============================ */

/** 复盘（将已完成的盘点任务回退到计划中重做） */
export const reviewStt = (data) =>
	requestInvAction(() => Request.requestJson(Request.PUT, "/review/review-stt", data));

/** 盘点差异过账 */
export const diffPost = (data) =>
	requestInvAction(() => Request.requestJson(Request.PUT, "/goods/diff-post", data));

/* ============================ 上架调整 ============================ */

/** 上架货物详情 */
export const getUpAdjustDetail = (id, success, fail) =>
	requestInv(
		() => Request.requestForm(Request.GET, "/lis/qurrydetail", { id }),
		success,
		fail,
	);

/** 修改上架货物 */
export const updateUpAdjust = (data) =>
	requestInvAction(() => Request.requestJson(Request.PUT, "/lis/adjustlistgoods", data));

/** 批量修改上架货物（body: 数组） */
export const batchUpdateUpAdjust = (list) =>
	requestInvAction(() => Request.requestJson(Request.PUT, "/addition-adjustment/batchmodify", list));

/* ============================ 下架调整 ============================ */

/** 下架货物详情 */
export const getRemovalDetail = (data, success, fail) =>
	requestInv(
		() => Request.requestForm(Request.GET, "/removal-adjustment/detail-query", data),
		success,
		fail,
	);

/** 修改下架货物 */
export const updateRemoval = (data) =>
	requestInvAction(() => Request.requestJson(Request.PUT, "/removal-adjustment/modify", data));

/** 批量修改下架货物（body: 数组） */
export const batchUpdateRemoval = (list) =>
	requestInvAction(() =>
		Request.requestJson(Request.PUT, "/removal-adjustment/batch-modify", list),
	);

/* ============================ 导出（blob 下载） ============================ */

/** 导出盘点任务 */
export const exportCheck = (data) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/inv/download", data, { responseType: "blob" }),
	);

/** 导出盘点差异数据 */
export const exportInventoryDifference = (data) =>
	requestBlob(() =>
		Request.requestForm(
			Request.GET,
			"/overall-inventory/difference-download",
			data,
			{ responseType: "blob" },
		),
	);

/** 导出复盘数据 */
export const exportReviewStt = (data) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/review/export-review-stt", data, { responseType: "blob" }),
	);

/** 导出盘点差异过账数据 */
export const exportDiffPost = (data) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/goods/export-diff-post", data, { responseType: "blob" }),
	);

/** 导出上架调整数据 */
export const exportUpAdjust = (data) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/lis/export-data", data, { responseType: "blob" }),
	);

/** 导出下架调整数据 */
export const exportRemoval = (data) =>
	requestBlob(() =>
		Request.requestForm(Request.GET, "/removal-adjustment/download", data, { responseType: "blob" }),
	);

/** 导出动仓盘点数据 */
export const exportMovingBin = (data) =>
	requestBlob(() =>
		Request.requestForm(
			Request.GET,
			"/moving-warehouse-inventory/download",
			data,
			{ responseType: "blob" },
		),
	);
