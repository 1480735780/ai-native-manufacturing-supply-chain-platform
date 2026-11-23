# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from patchlib import patch
R = "wms-cpp/wms-c7-reposity/"

# ==================== 订单类型：Controller 实现 ====================
patch(R+"controller/ordertypes/OrderTypesController.cpp",
"""\tif (service.removeData(id)){
\t\tjvo->success(idValue);
\t}
\telse
\t{
\t\tjvo->fail(idValue);
\t}
\t// 响应结果
\treturn jvo;
}""",
"""\tif (service.removeData(id)){
\t\tjvo->success(idValue);
\t}
\telse
\t{
\t\tjvo->fail(idValue);
\t}
\t// 响应结果
\treturn jvo;
}

Uint64JsonVO::Wrapper OrderTypesController::execDeleteOrdBatch(const oatpp::String& ids)
{
\t// 定义返回数据对象
\tauto jvo = Uint64JsonVO::createShared();
\t// 参数校验
\tif (!ids || ids->empty())
\t{
\t\tjvo->init(UInt64(-1), RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\t// 定义一个Service
\tOrderTypesService service;
\t// 执行批量删除
\tif (service.removeDataBatch(ids->c_str())) {
\t\tjvo->success(UInt64(1));
\t}
\telse
\t{
\t\tjvo->fail(UInt64(-1));
\t}
\t// 响应结果
\treturn jvo;
}""")

# ==================== 作业类型：DAO ====================
patch(R+"dao/ba_act_type/BaActTypeDAO.h",
"""\tint deleteById(const std::string id);""",
"""\tint deleteById(const std::string id);

\t// 通过ID列表（逗号分隔）批量删除数据
\tint deleteByIds(const std::string& ids);""")

patch(R+"dao/ba_act_type/BaActTypeDAO.cpp",
"""int BaActTypeDAO::deleteById(const std::string id)
{
    std::string sql = "DELETE FROM `ba_act_type` WHERE `id`=?";

    return sqlSession->executeUpdate(sql, "%s", id);
}""",
"""int BaActTypeDAO::deleteById(const std::string id)
{
    std::string sql = "DELETE FROM `ba_act_type` WHERE `id`=?";

    return sqlSession->executeUpdate(sql, "%s", id);
}

int BaActTypeDAO::deleteByIds(const std::string& ids)
{
    if (ids.empty())
    {
        return 0;
    }
    // 将逗号分隔的id拆分为参数，避免拼接字符串造成的注入风险
    std::vector<std::string> idList;
    std::string item;
    std::stringstream ss(ids);
    while (std::getline(ss, item, ','))
    {
        if (!item.empty())
        {
            idList.push_back(item);
        }
    }
    if (idList.empty())
    {
        return 0;
    }
    std::string sql = "DELETE FROM `ba_act_type` WHERE `id` IN (";
    SqlParams params;
    for (size_t i = 0; i < idList.size(); i++)
    {
        if (i > 0)
        {
            sql += ",";
        }
        sql += "?";
        SQLPARAMS_PUSH(params, "s", std::string, idList[i]);
    }
    sql += ")";
    return sqlSession->executeUpdate(sql, params);
}""")

# ==================== 作业类型：Service ====================
patch(R+"service/ba_act_type/BaActTypeService.h",
"""    // 删除作业类型数据
    bool removeData(const std::string id);""",
"""    // 删除作业类型数据
    bool removeData(const std::string id);
    // 通过ID列表（逗号分隔）批量删除作业类型数据
    bool removeDataBatch(const std::string& ids);""")

patch(R+"service/ba_act_type/BaActTypeService.cpp",
"""bool BaActTypeService::removeData(const std::string _id)
{
    //uint64_t id = stoi(_id);
    BaActTypeDAO dao;
    // 将数字 id 转换为字符串后删除
    return dao.deleteById(_id) == 1;
}""",
"""bool BaActTypeService::removeData(const std::string _id)
{
    //uint64_t id = stoi(_id);
    BaActTypeDAO dao;
    // 将数字 id 转换为字符串后删除
    return dao.deleteById(_id) == 1;
}

bool BaActTypeService::removeDataBatch(const std::string& ids)
{
    BaActTypeDAO dao;
    // 批量删除作业类型
    return dao.deleteByIds(ids) > 0;
}""")
