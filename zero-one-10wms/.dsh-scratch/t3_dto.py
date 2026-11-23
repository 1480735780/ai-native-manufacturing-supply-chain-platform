# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

p = "wms-cpp/wms-c7-reposity/domain/dto/library/LibraryDTO.h"
enc = detect(open(p, 'rb').read())
print("原编码:", enc)

new = '''#pragma once
/*
 @Author: nanbowan
*/
#include"../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/*
* 修改库位类型定义自动生成
*/
class ModifyLibraryDTO :public oatpp::DTO
{
\tDTO_INIT(ModifyLibraryDTO, DTO);

\t//要修改的库位类型的唯一id
\tAPI_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("dictionary.library.id.summary"));

\t//新库位类型使用
\tAPI_DTO_FIELD_DEFAULT(String, bin_type_code, ZH_WORDS_GETTER("dictionary.library.code.summary"));

\t//新库位类型名称
\tAPI_DTO_FIELD_DEFAULT(String, bin_type_name, ZH_WORDS_GETTER("dictionary.library.type.summary"));

};


/**
 * 库位类型数据对象（编码 + 名称）
 */
class LibraryDTO : public oatpp::DTO
{
\tDTO_INIT(LibraryDTO, oatpp::DTO);

\t//库位类型代码
\tAPI_DTO_FIELD_DEFAULT(String, bin_type_code, ZH_WORDS_GETTER("dictionary.library.code.summary"));

\t//库位类型名称
\tAPI_DTO_FIELD_DEFAULT(String, bin_type_name, ZH_WORDS_GETTER("dictionary.library.type.summary"));

};


/**
 * 库位类型详细数据对象（含审计字段，供新增/修改使用）
 */
class LibraryDetailDTO : public oatpp::DTO
{
\tDTO_INIT(LibraryDetailDTO, oatpp::DTO);

\t//唯一id
\tAPI_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("dictionary.library.id.summary"));

\t//创建人名称
\tAPI_DTO_FIELD_DEFAULT(String, create_name, ZH_WORDS_GETTER("dictionary.library.field.create_name"));
\t//创建人登录名称
\tAPI_DTO_FIELD_DEFAULT(String, create_by, ZH_WORDS_GETTER("dictionary.library.field.create_by"));
\t//创建日期
\tAPI_DTO_FIELD_DEFAULT(String, create_date, ZH_WORDS_GETTER("dictionary.library.field.create_date"));
\t//更新人名称
\tAPI_DTO_FIELD_DEFAULT(String, update_name, ZH_WORDS_GETTER("dictionary.library.field.update_name"));
\t//更新人登录名称
\tAPI_DTO_FIELD_DEFAULT(String, update_by, ZH_WORDS_GETTER("dictionary.library.field.update_by"));
\t//更新日期
\tAPI_DTO_FIELD_DEFAULT(String, update_date, ZH_WORDS_GETTER("dictionary.library.field.update_date"));
\t//所属部门
\tAPI_DTO_FIELD_DEFAULT(String, sys_org_code, ZH_WORDS_GETTER("dictionary.library.field.sys_org_code"));
\t//所属公司
\tAPI_DTO_FIELD_DEFAULT(String, sys_company_code, ZH_WORDS_GETTER("dictionary.library.field.sys_company_code"));

\t//库位类型代码
\tAPI_DTO_FIELD_DEFAULT(String, bin_type_code, ZH_WORDS_GETTER("dictionary.library.code.summary"));
\t//库位类型名称
\tAPI_DTO_FIELD_DEFAULT(String, bin_type_name, ZH_WORDS_GETTER("dictionary.library.type.summary"));

};


/**
 * 新增库位类型请求对象（不提供 id，由后端生成）
 */
class LibraryAddDTO : public LibraryDTO
{
\tDTO_INIT(LibraryAddDTO, LibraryDTO);

};


/**
 * 库位类型列表数据对象（列表行操作需要唯一标识）
 */
class LibraryListDTO : public LibraryDTO
{
\tDTO_INIT(LibraryListDTO, LibraryDTO);

\t//唯一id
\tAPI_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("dictionary.library.id.summary"));
};


/**
 * 库位类型名称对象：唯一标识 + 代码 + 名称
 */
class LibraryNameDTO : public oatpp::DTO
{
\tDTO_INIT(LibraryNameDTO, oatpp::DTO);

\t//唯一id
\tAPI_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("dictionary.library.id.summary"));
\t//库位类型代码
\tAPI_DTO_FIELD_DEFAULT(String, bin_type_code, ZH_WORDS_GETTER("dictionary.library.code.summary"));
\t//库位类型名称
\tAPI_DTO_FIELD_DEFAULT(String, bin_type_name, ZH_WORDS_GETTER("dictionary.library.type.summary"));
};


/**
 * 库位类型列表分页数据对象
 */
class LibraryPageDTO : public PageDTO<LibraryListDTO::Wrapper>
{
\tDTO_INIT(LibraryPageDTO, PageDTO<LibraryListDTO::Wrapper>);
};


#include OATPP_CODEGEN_END(DTO)
'''

open(p, 'wb').write(new.encode(enc))
print("已写入, 编码:", enc)
