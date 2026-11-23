# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from patchlib import patch
R = "wms-cpp/wms-c7-reposity/"

patch(R+"service/ba_act_type/BaActTypeService.h",
"""    // 删除作业类型
    bool removeData(const std::string id);""",
"""    // 删除作业类型
    bool removeData(const std::string id);
    // 通过ID列表（逗号分隔）批量删除作业类型
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

# ==================== 作业类型：Controller 头（新增端点 + 修复路由） ====================
patch(R+"controller/ba_act_type/BaActTypeController.h",
"""    // 3 定义修改接口处理
    API_HANDLER_ENDPOINT_AUTH(API_M_PUT, "/baActType", modifyBaActType, BODY_DTO(BaActTypeDTO::Wrapper, dto), execModifyBaActType(dto));""",
"""    // 3 定义修改接口处理
    API_HANDLER_ENDPOINT_AUTH(API_M_PUT, "/repository/modify-baacttype", modifyBaActType, BODY_DTO(BaActTypeDTO::Wrapper, dto), execModifyBaActType(dto));""")

patch(R+"controller/ba_act_type/BaActTypeController.h",
"""    // 4 定义删除接口处理
    API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/repository/delete-baacttype/{id}", removeBaActType, PATH(String, id), execRemoveBaActType(id));""",
"""    // 4 定义删除接口处理
    API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/repository/delete-baacttype/{id}", removeBaActType, PATH(String, id), execRemoveBaActType(id));

    // 5 定义批量删除接口描述
    ENDPOINT_INFO(removeBaActTypeBatch) {
        // 定义标题和返回类型以及授权支持
        API_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("ba_act_type.delete-batch.summary"), Uint64JsonVO::Wrapper);
        // 定义路径参数说明
        API_DEF_ADD_PATH_PARAMS(String, "ids", ZH_WORDS_GETTER("ba_act_type.delete-batch.summary"), "id1,id2", true);
    }
    // 5 定义批量删除接口处理
    API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/repository/delete-baacttype-batch/{ids}", removeBaActTypeBatch, PATH(String, ids), execRemoveBaActTypeBatch(ids));""")

patch(R+"controller/ba_act_type/BaActTypeController.h",
"""    API_HANDLER_ENDPOINT(API_M_POST, "reposity/upload-baacttypefile", uploadFile, REQUEST(std::shared_ptr<IncomingRequest>, request), execUploadOne(request));""",
"""    API_HANDLER_ENDPOINT(API_M_POST, "/repository/upload-baacttypefile", uploadFile, REQUEST(std::shared_ptr<IncomingRequest>, request), execUploadOne(request));""")

patch(R+"controller/ba_act_type/BaActTypeController.h",
"""    ENDPOINT(API_M_GET, "reposity/download-baacttypefile", downloadFile, QUERY(String, filename)) {""",
"""    ENDPOINT(API_M_GET, "/repository/download-baacttypefile", downloadFile, QUERY(String, filename)) {""")

patch(R+"controller/ba_act_type/BaActTypeController.h",
"""    // 4 作业类型删除数据
    StringJsonVO::Wrapper execRemoveBaActType(const String& id);""",
"""    // 4 作业类型删除数据
    StringJsonVO::Wrapper execRemoveBaActType(const String& id);
    // 5 作业类型批量删除数据
    StringJsonVO::Wrapper execRemoveBaActTypeBatch(const String& ids);""")
