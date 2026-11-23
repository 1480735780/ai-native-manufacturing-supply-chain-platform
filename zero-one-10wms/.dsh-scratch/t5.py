# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from patchlib import patch
R = "wms-cpp/wms-c7-reposity/"

# ==================== 订单类型：DAO ====================
patch(R+"dao/ordertypes/OrderTypesDAO.h",
"""\t// 通过ID删除数据
\tint deleteById(string id);
};""",
"""\t// 通过ID删除数据
\tint deleteById(string id);
\t// 通过ID列表（逗号分隔）批量删除数据
\tint deleteByIds(const std::string& ids);
};""")

patch(R+"dao/ordertypes/OrderTypesDAO.cpp",
"""int OrderTypesDAO::deleteById(string id)
{
\tif (id == "0") {
\t\tstring sql = "DELETE FROM `ba_order_type` ";
\t\tsqlSession->executeUpdate(sql);
\t\treturn 1;
\t}

\tstring sql = "DELETE FROM `ba_order_type` WHERE `id`=?";
\treturn sqlSession->executeUpdate(sql, "%s", id);
}""",
"""int OrderTypesDAO::deleteById(string id)
{
\tif (id == "0") {
\t\tstring sql = "DELETE FROM `ba_order_type` ";
\t\tsqlSession->executeUpdate(sql);
\t\treturn 1;
\t}

\tstring sql = "DELETE FROM `ba_order_type` WHERE `id`=?";
\treturn sqlSession->executeUpdate(sql, "%s", id);
}

int OrderTypesDAO::deleteByIds(const std::string& ids)
{
\tif (ids.empty())
\t{
\t\treturn 0;
\t}
\t// 将逗号分隔的id拆分为参数，避免拼接字符串造成的注入风险
\tstd::vector<std::string> idList;
\tstd::string item;
\tstd::stringstream ss(ids);
\twhile (std::getline(ss, item, ','))
\t{
\t\tif (!item.empty())
\t\t{
\t\t\tidList.push_back(item);
\t\t}
\t}
\tif (idList.empty())
\t{
\t\treturn 0;
\t}
\tstring sql = "DELETE FROM `ba_order_type` WHERE `id` IN (";
\tSqlParams params;
\tfor (size_t i = 0; i < idList.size(); i++)
\t{
\t\tif (i > 0)
\t\t{
\t\t\tsql += ",";
\t\t}
\t\tsql += "?";
\t\tSQLPARAMS_PUSH(params, "s", std::string, idList[i]);
\t}
\tsql += ")";
\treturn sqlSession->executeUpdate(sql, params);
}""")

# ==================== 订单类型：Service ====================
patch(R+"service/ordertypes/OrderTypesService.h",
"""\t// 通过ID删除数据
\tbool removeData(string id);;
};""",
"""\t// 通过ID删除数据
\tbool removeData(string id);
\t// 通过ID列表（逗号分隔）批量删除数据
\tbool removeDataBatch(const std::string& ids);
};""")

patch(R+"service/ordertypes/OrderTypesService.cpp",
"""bool OrderTypesService::removeData(string id)
{
\tOrderTypesDAO dao;
\treturn dao.deleteById(id) == 1;
}""",
"""bool OrderTypesService::removeData(string id)
{
\tOrderTypesDAO dao;
\treturn dao.deleteById(id) == 1;
}

bool OrderTypesService::removeDataBatch(const std::string& ids)
{
\tOrderTypesDAO dao;
\treturn dao.deleteByIds(ids) > 0;
}""")

# ==================== 订单类型：Controller 头 ====================
patch(R+"controller/ordertypes/OrderTypesController.h",
"""    // 3.2 定义删除接口处理
    API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/repository/ord-delete/{id}", deleteOrd, PATH(oatpp::String, id), execDeleteOrd(id));

private:
    Uint64JsonVO::Wrapper execModifyOrd(const ModifyOrderTypeDTO::Wrapper& dto);

    Uint64JsonVO::Wrapper execDeleteOrd(const oatpp::String& id);
};""",
"""    // 3.2 定义删除接口处理
    API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/repository/ord-delete/{id}", deleteOrd, PATH(oatpp::String, id), execDeleteOrd(id));

    // 4.1 定义批量删除接口描述
    ENDPOINT_INFO(deleteOrdBatch) {
        // 定义标题和返回类型以及授权支持
        API_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("dictionary.ope.delete-batch.summary"), Uint64JsonVO::Wrapper);
        // 定义路径参数说明
        API_DEF_ADD_PATH_PARAMS(String, "ids", ZH_WORDS_GETTER("dictionary.ope.delete-batch.summary"), "id1,id2", true);
    }
    // 4.2 定义批量删除接口处理
    API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/repository/ord-delete-batch/{ids}", deleteOrdBatch, PATH(oatpp::String, ids), execDeleteOrdBatch(ids));

private:
    Uint64JsonVO::Wrapper execModifyOrd(const ModifyOrderTypeDTO::Wrapper& dto);

    Uint64JsonVO::Wrapper execDeleteOrd(const oatpp::String& id);

    Uint64JsonVO::Wrapper execDeleteOrdBatch(const oatpp::String& ids);
};""")
