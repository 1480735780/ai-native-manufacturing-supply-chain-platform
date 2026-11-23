// 库存管理（j6-stockln）
import Request from "../request";

const requestStock = async (request, success, fail) => {
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

/** 库存查询（条件+分页） */
export const listStock = (data, success, fail) =>
	requestStock(() => Request.requestForm(Request.GET, "/stock/inventory-query/query-all", data), success, fail);

/** 导出库存报表 */
export const exportStock = async (params) => {
	const res = await Request.requestForm(Request.GET, "/stock/inventory-query/export", params, {
		responseType: "blob",
	});
	return res.data;
};
