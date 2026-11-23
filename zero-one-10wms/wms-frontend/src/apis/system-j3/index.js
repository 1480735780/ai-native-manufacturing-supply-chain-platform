// 系统管理（j3）：数据字典 / 系统图标 / 国际化语言 / 分类管理
import Request from "../request";

const requestJ3 = async (request, success, fail) => {
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

/* ============================ 数据字典 ============================ */

/** 字典分类列表（条件+分页） */
export const listTypeGroups = (data, success, fail) =>
	requestJ3(() => Request.requestForm(Request.GET, "/j3sysmanager/sysmanager/typegroup/query", data), success, fail);

/** 录入字典分类 */
export const addTypeGroup = (data) =>
	Request.requestJson(Request.POST, "/j3sysmanager/sysmanager/typegroup/add", data);

/** 修改字典分类 */
export const modifyTypeGroup = (data) =>
	Request.requestJson(Request.PUT, "/j3sysmanager/sysmanager/typegroup/modify", data);

/** 删除字典分类 */
export const removeTypeGroup = (id) =>
	Request.requestForm(Request.DELETE, `/j3sysmanager/sysmanager/typegroup/remove/${id}`);

/** 字典类型列表（条件+分页，必须传 typegroupid） */
export const listTypes = (data, success, fail) =>
	requestJ3(() => Request.requestForm(Request.GET, "/j3sysmanager/sysmanager/type/query", data), success, fail);

/** 通过分类编码获取字典类型名称列表 */
export const listTypesByGroupCode = (typegroupCode) =>
	Request.requestForm(Request.GET, "/j3sysmanager/sysmanager/type/query-bygroupcode", { typegroupCode });

/** 录入字典类型 */
export const addType = (data) => Request.requestJson(Request.POST, "/j3sysmanager/sysmanager/type/add", data);

/** 修改字典类型 */
export const modifyType = (data) => Request.requestJson(Request.POST, "/j3sysmanager/sysmanager/type/modify", data);

/** 删除字典类型 */
export const removeType = (id) =>
	Request.requestForm(Request.DELETE, `/j3sysmanager/sysmanager/type/remove/${id}`);

/* ============================ 系统图标 ============================ */

/** 系统图标列表（分页） */
export const listIcons = (data, success, fail) =>
	requestJ3(() => Request.requestForm(Request.GET, "/j3sysmanager/sysmanager/icons/all", data), success, fail);

/** 图标名称列表（按类型） */
export const listIconNames = (type) =>
	Request.requestForm(Request.GET, "/j3sysmanager/sysmanager/icons/names", { type });

/** 图标详情（回显） */
export const getIconDetail = (id) => Request.requestForm(Request.GET, `/j3sysmanager/sysmanager/icons/${id}`);

/** 录入图标（multipart：name / type / iconclas / file） */
export const addIcon = (data) => Request.postFile("/j3sysmanager/sysmanager/icons/add", data);

/** 修改图标（multipart：id / name / type / iconclas / file，需重新选择文件） */
export const modifyIcon = (data) => Request.postFile("/j3sysmanager/sysmanager/icons/modify", data);

/** 删除图标 */
export const removeIcon = (id) =>
	Request.requestForm(Request.DELETE, `/j3sysmanager/sysmanager/icons/delete?id=${id}`);

/* ============================ 国际化语言 ============================ */

/** 国际化语言列表（POST 查询，langKey/langContext 必须传空串而不是 null） */
export const listMultiLang = (data, success, fail) =>
	requestJ3(
		() =>
			Request.requestJson(Request.POST, "/j3sysmanager/sysmanager/lang/multilang", {
				pageIndex: 1,
				pageSize: 10,
				langKey: "",
				langContext: "",
				sort: "id",
				order: "asc",
				...data,
			}),
		success,
		fail,
	);

/** 刷新语言缓存 */
export const refreshLangCache = () =>
	Request.requestForm(Request.GET, "/j3sysmanager/sysmanager/lang/refresh-cache");

/** 录入语言对照 */
export const addLang = (data) => Request.requestJson(Request.POST, "/j3sysmanager/sysmanager/lang/addlang", data);

/** 修改语言对照 */
export const updateLang = (data) =>
	Request.requestJson(Request.POST, "/j3sysmanager/sysmanager/lang/updatelang", data);

/** 删除语言对照 */
export const removeLang = (id) =>
	Request.requestForm(Request.GET, `/j3sysmanager/sysmanager/lang/deletelang?id=${id}`);

/* ============================ 分类管理 ============================ */

/** 分类名称树 */
export const listCatagoryTree = (success, fail) =>
	requestJ3(() => Request.requestForm(Request.GET, "/j3sysmanager/sysmanager/catagory/query-catagory-tree"), success, fail);

/** 分类列表（传 catagoryId 则查子分类，否则查根分类） */
export const listCatagories = (data, success, fail) =>
	requestJ3(
		() => Request.requestForm(Request.GET, "/j3sysmanager/sysmanager/catagory/query-catagory-list", data),
		success,
		fail,
	);

/** 新增分类 */
export const addCatagory = (data) =>
	Request.requestJson(Request.POST, "/j3sysmanager/sysmanager/catagory/add-catagory", data);

/** 修改分类 */
export const modifyCatagory = (data) =>
	Request.requestJson(Request.PUT, "/j3sysmanager/sysmanager/catagory/modify-catagory", data);

/** 删除分类 */
export const removeCatagory = (id) =>
	Request.requestJson(Request.DELETE, "/j3sysmanager/sysmanager/catagory/remove-catagory", { id });
