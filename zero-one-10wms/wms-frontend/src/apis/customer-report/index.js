// 客户报表（客户库存 / 效期预警）
import Request from "../request";

/**
 * 客户库存（Java j6-stockln，视图 mv_stock_cus）
 */
export const listCustomerStock = async (data, success, fail) => {
	try {
		const res = await Request.requestForm(Request.GET, "/stock/customer-stock/query-all", data);
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
 * 效期预警（Java j6-stockln，视图 mv_stock_yj）
 */
export const listExpiryWarning = async (data, success, fail) => {
	try {
		const res = await Request.requestForm(Request.GET, "/stock/expiry-warning/query-all", data);
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
