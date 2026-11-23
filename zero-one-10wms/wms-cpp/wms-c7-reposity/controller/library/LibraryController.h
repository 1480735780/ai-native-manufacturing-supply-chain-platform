/*
 @Author: nanbowan
*/
#ifndef _Deg_CONTROLLER_
#define _Deg_CONTROLLER_

#include "domain/GlobalInclude.h"
#include"domain/vo/BaseJsonVO.h"
#include "domain/vo/library/LibraryVO.h"
#include "domain/dto/library/LibraryDTO.h"
#include "domain/query/library/LibraryQuery.h"
#include "../../lib-common/include/id/UuidFacade.h"

#include OATPP_CODEGEN_BEGIN(ApiController)


class LibraryController : public oatpp::web::server::api::ApiController
{
    API_ACCESS_DECLARE(LibraryController);

public:
     //定义修改接口描述
    API_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("dictionary.libraryope.modify.summary"), modifyLibrary, Uint64JsonVO::Wrapper);
    // 定义修改接口处理
    API_HANDLER_ENDPOINT_AUTH(API_M_PUT, "/repository/library/modify", modifyLibrary, BODY_DTO(ModifyLibraryDTO::Wrapper, dto), execModifyLibrary(dto));

    // 3.1 定义删除接口描述
    ENDPOINT_INFO(deleteLibrary) {
        // 定义标题和返回类型以及授权支持
        API_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("dictionary.libraryope.delete.summary"), Uint64JsonVO::Wrapper);
        // 定义其他路径参数说明
        API_DEF_ADD_PATH_PARAMS(UInt64, "id", ZH_WORDS_GETTER("dictionary.libraryope.delete.summary"), 1, true);
    }
    // 3.2 定义删除接口处理
    API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/repository/library/{id}", deleteLibrary, PATH(oatpp::String, id), execDeleteLibrary(id));

    // 4.1 定义库位类型列表查询接口描述
    ENDPOINT_INFO(queryLibrary) {
        // 定义接口标题
        API_DEF_ADD_TITLE(ZH_WORDS_GETTER("dictionary.libraryope.query-all.summary"));
        // 定义默认授权参数
        API_DEF_ADD_AUTH();
        // 定义响应参数格式
        API_DEF_ADD_RSP_JSON_WRAPPER(LibraryPageJsonVO);
        // 定义分页查询参数描述
        API_DEF_ADD_PAGE_PARAMS();
        // 定义其他查询参数描述
        API_DEF_ADD_QUERY_PARAMS(String, "bin_type_code", ZH_WORDS_GETTER("dictionary.library.code.summary"), "BT001", false);
        API_DEF_ADD_QUERY_PARAMS(String, "bin_type_name", ZH_WORDS_GETTER("dictionary.library.type.summary"), "常规库位", false);
    }
    // 4.2 定义库位类型列表查询接口处理
    ENDPOINT(API_M_GET, "/repository/library/query-all", queryLibrary, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
        // 解析查询参数为Query领域模型
        API_HANDLER_QUERY_PARAM(libraryQuery, LibraryQuery, queryParams);
        // 呼叫执行函数响应结果
        API_HANDLER_RESP_VO(execQueryLibrary(libraryQuery));
    }

    // 5.1 定义库位类型录入接口描述
    ENDPOINT_INFO(addLibrary) {
        // 定义接口标题
        API_DEF_ADD_TITLE(ZH_WORDS_GETTER("dictionary.libraryope.add.summary"));
        // 定义默认授权参数
        API_DEF_ADD_AUTH();
        // 定义响应参数格式
        API_DEF_ADD_RSP_JSON_WRAPPER(Uint64JsonVO);
    }
    // 5.2 定义库位类型录入接口处理
    ENDPOINT(API_M_POST, "/repository/library/add", addLibrary, BODY_DTO(LibraryAddDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
        // 呼叫执行函数响应结果
        API_HANDLER_RESP_VO(execAddLibrary(dto, authObject->getPayload()));
    }

    // 6.1 定义库位类型名称列表接口描述
    ENDPOINT_INFO(queryLibraryName) {
        // 定义接口标题
        API_DEF_ADD_TITLE(ZH_WORDS_GETTER("dictionary.libraryope.query-name.summary"));
        // 定义默认授权参数
        API_DEF_ADD_AUTH();
        // 定义响应参数格式
        API_DEF_ADD_RSP_JSON_WRAPPER(LibraryNameListJsonVO);
    }
    // 6.2 定义库位类型名称列表接口处理
    ENDPOINT(API_M_GET, "/repository/library/query-name", queryLibraryName, API_HANDLER_AUTH_PARAME) {
        // 呼叫执行函数响应结果
        API_HANDLER_RESP_VO(execQueryLibraryName());
    }


private:
    Uint64JsonVO::Wrapper execModifyLibrary(const ModifyLibraryDTO::Wrapper& dto);

    Uint64JsonVO::Wrapper execDeleteLibrary(const oatpp::String& id);

    // 库位类型列表查询
    LibraryPageJsonVO::Wrapper execQueryLibrary(const LibraryQuery::Wrapper& query);

    // 库位类型录入
    Uint64JsonVO::Wrapper execAddLibrary(const LibraryAddDTO::Wrapper& dto, const PayloadDTO& payload);

    // 库位类型名称列表查询
    LibraryNameListJsonVO::Wrapper execQueryLibraryName();
};

#include OATPP_CODEGEN_END(ApiController)

#endif // _Deg_CONTROLLER_
