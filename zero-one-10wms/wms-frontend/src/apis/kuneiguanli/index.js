// 库内管理：托盘转移 / 储位转移 / 库内转移
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

/** 托盘转移-可转移列表 */
export const listTinTransfer = (data, success, fail) =>
	requestInv(
		() =>
			Request.requestForm(
				Request.GET,
				"/kuneiguanli/shengchengtuopanzhuanyi/query-tin-transfer-list",
				data,
			),
		success,
		fail,
	);

/** 托盘转移-批量生成任务 */
export const generateTinTransfer = (data, success, fail) =>
	requestInv(
		() =>
			Request.requestJson(
				Request.PUT,
				"/kuneiguanli/shengchengtuopanzhuanyi/modify-tin-transfer",
				data,
			),
		success,
		fail,
	);

/** 储位转移-可移动列表 */
export const listBinTransfer = (data, success, fail) =>
	requestInv(
		() =>
			Request.requestForm(
				Request.GET,
				"/kuneiguanli/shengchengchuweizhuanyi/query-bin-transfer",
				data,
			),
		success,
		fail,
	);

/** 储位转移-批量生成任务 */
export const generateBinTransfer = (data, success, fail) =>
	requestInv(
		() =>
			Request.requestJson(
				Request.PUT,
				"/kuneiguanli/shengchengchuweizhuanyi/modify-bin-transfer",
				data,
			),
		success,
		fail,
	);

/** 库内转移-任务列表 */
export const listMoveGoods = (data, success, fail) =>
	requestInv(
		() =>
			Request.requestForm(Request.GET, "/kuneiguanli/kuneizhuanyi/query-move-goods-list", data),
		success,
		fail,
	);

/** 库内转移-任务详情 */
export const getMoveGoodsDetail = (id, success, fail) =>
	requestInv(
		() =>
			Request.requestForm(Request.GET, "/kuneiguanli/kuneizhuanyi/query-detailed-move-goods", {
				id,
			}),
		success,
		fail,
	);

/** 库内转移-修改任务 */
export const modifyMoveGoods = (data, success, fail) =>
	requestInv(
		() =>
			Request.requestJson(Request.PUT, "/kuneiguanli/kuneizhuanyi/modify-move-goods", data),
		success,
		fail,
	);

/** 库内转移-批量转移 */
export const batchMoveGoods = (data, success, fail) =>
	requestInv(
		() => Request.requestJson(Request.PUT, "/kuneiguanli/kuneizhuanyi/batch-move-goods", data),
		success,
		fail,
	);

/** 库内转移-批量删除 */
export const removeMoveGoods = (ids, success, fail) =>
	requestInv(
		() =>
			Request.requestForm(Request.DELETE, "/kuneiguanli/kuneizhuanyi/batch-remove-move-goods", {
				ids: ids.join(","),
			}),
		success,
		fail,
	);

/** 库内转移-导出数据（返回文件流） */
export const downloadMoveGoods = (ids) =>
	Request.requestForm(
		Request.GET,
		"/kuneiguanli/kuneizhuanyi/down-load-move-goods",
		{ ids: ids.join(",") },
		{ responseType: "blob" },
	);
