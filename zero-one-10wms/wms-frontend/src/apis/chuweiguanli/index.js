// 储位管理（wms-c3-chuweiguanli）接口
import Request from "../request";

const cleanParams = data => {
	const result = {};
	Object.keys(data || {}).forEach(key => {
		const value = data[key];
		if (value !== "" && value !== null && value !== undefined) {
			result[key] = value;
		}
	});
	return result;
};

/** 列表查询统一封装：成功回调分页数据 {pageIndex, pageSize, total, pages, rows}，失败回调 */
const requestList = async (url, data, success, fail) => {
	try {
		const res = await Request.requestForm(Request.GET, url, cleanParams(data));
		if (res.data !== undefined && res.data !== null) {
			success(res.data);
			return;
		}
		throw res;
	} catch (err) {
		console.warn(err);
		fail(err);
	}
};

/** 仓储定义-仓库名称下拉列表 */
export const getStoreNameList = (success, fail) =>
	requestList("/chuweiguanli/cangkudingyi/query-cangku-name-list", {}, success, fail);

/** 储位信息分页查询（条件：仓库/库位编码/库位条码/库位类型/xyz 坐标） */
export const queryChuweiList = (data, success, fail) =>
	requestList("/chuweiguanli/chuweidingyi/query-chuwei", data, success, fail);

/** 空储位分页查询 */
export const queryKongChuweiList = (data, success, fail) =>
	requestList("/chuweiguanli/kongchuwei/get-kongchuwei-list", data, success, fail);

/** 可用储位分页查询 */
export const queryUsefulBinList = (data, success, fail) =>
	requestList("/chuweiguanli/keyongchuwei/query-usefulbin-list", data, success, fail);

/** 仓位图数据查询（列表：仓库/库位编码/xnode 行/ynode 列/znode 层/colour 颜色/tincount 托盘数） */
export const queryCangweiMap = (data, success, fail) =>
	requestList("/chuweiguanli/cangweitu/query-store", data, success, fail);

/** 保存二进制内容为文件下载 */
export const saveBlob = (blob, filename) => {
	const url = window.URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
	window.URL.revokeObjectURL(url);
};

/** 储位明细导出（POST，body: {biaoshi: [库位编码]}，空数组导出全部，返回 Excel 文件流） */
export const exportChuweiDetail = (success, fail) =>
	Request.requestJson(Request.POST, "/chuweiguanli/chuweidingyi/dao-chu-chu-wei", { biaoshi: [] }, { responseType: "blob" })
		.then(res => {
			const blob = res && res.data;
			if (blob && blob.size > 0) {
				success(blob);
				return;
			}
			throw new Error("导出内容为空");
		})
		.catch(err => {
			console.warn(err);
			fail(err);
		});

/** 储位明细导入（multipart 上传，后端读取字段名 file0、file1...） */
export const importChuweiDetail = (file, success, fail) =>
	Request.postFile("/chuweiguanli/chuweidingyi/dao-ru-chu-wei", { file0: file })
		.then(res => {
			success(res);
		})
		.catch(err => {
			console.warn(err);
			fail(err);
		});
