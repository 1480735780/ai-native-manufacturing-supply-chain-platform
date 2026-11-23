#pragma once
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
	DTO_INIT(ModifyLibraryDTO, DTO);

	//要修改的库位类型的唯一id
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("dictionary.library.id.summary"));

	//新库位类型使用
	API_DTO_FIELD_DEFAULT(String, bin_type_code, ZH_WORDS_GETTER("dictionary.library.code.summary"));

	//新库位类型名称
	API_DTO_FIELD_DEFAULT(String, bin_type_name, ZH_WORDS_GETTER("dictionary.library.type.summary"));

};


/**
 * 库位类型数据对象（编码 + 名称）
 */
class LibraryDTO : public oatpp::DTO
{
	DTO_INIT(LibraryDTO, oatpp::DTO);

	//库位类型代码
	API_DTO_FIELD_DEFAULT(String, bin_type_code, ZH_WORDS_GETTER("dictionary.library.code.summary"));

	//库位类型名称
	API_DTO_FIELD_DEFAULT(String, bin_type_name, ZH_WORDS_GETTER("dictionary.library.type.summary"));

};


/**
 * 库位类型详细数据对象（含审计字段，供新增/修改使用）
 */
class LibraryDetailDTO : public oatpp::DTO
{
	DTO_INIT(LibraryDetailDTO, oatpp::DTO);

	//唯一id
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("dictionary.library.id.summary"));

	//创建人名称
	API_DTO_FIELD_DEFAULT(String, create_name, ZH_WORDS_GETTER("dictionary.library.field.create_name"));
	//创建人登录名称
	API_DTO_FIELD_DEFAULT(String, create_by, ZH_WORDS_GETTER("dictionary.library.field.create_by"));
	//创建日期
	API_DTO_FIELD_DEFAULT(String, create_date, ZH_WORDS_GETTER("dictionary.library.field.create_date"));
	//更新人名称
	API_DTO_FIELD_DEFAULT(String, update_name, ZH_WORDS_GETTER("dictionary.library.field.update_name"));
	//更新人登录名称
	API_DTO_FIELD_DEFAULT(String, update_by, ZH_WORDS_GETTER("dictionary.library.field.update_by"));
	//更新日期
	API_DTO_FIELD_DEFAULT(String, update_date, ZH_WORDS_GETTER("dictionary.library.field.update_date"));
	//所属部门
	API_DTO_FIELD_DEFAULT(String, sys_org_code, ZH_WORDS_GETTER("dictionary.library.field.sys_org_code"));
	//所属公司
	API_DTO_FIELD_DEFAULT(String, sys_company_code, ZH_WORDS_GETTER("dictionary.library.field.sys_company_code"));

	//库位类型代码
	API_DTO_FIELD_DEFAULT(String, bin_type_code, ZH_WORDS_GETTER("dictionary.library.code.summary"));
	//库位类型名称
	API_DTO_FIELD_DEFAULT(String, bin_type_name, ZH_WORDS_GETTER("dictionary.library.type.summary"));

};


/**
 * 新增库位类型请求对象（不提供 id，由后端生成）
 */
class LibraryAddDTO : public LibraryDTO
{
	DTO_INIT(LibraryAddDTO, LibraryDTO);

};


/**
 * 库位类型列表数据对象（列表行操作需要唯一标识）
 */
class LibraryListDTO : public LibraryDTO
{
	DTO_INIT(LibraryListDTO, LibraryDTO);

	//唯一id
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("dictionary.library.id.summary"));
};


/**
 * 库位类型名称对象：唯一标识 + 代码 + 名称
 */
class LibraryNameDTO : public oatpp::DTO
{
	DTO_INIT(LibraryNameDTO, oatpp::DTO);

	//唯一id
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("dictionary.library.id.summary"));
	//库位类型代码
	API_DTO_FIELD_DEFAULT(String, bin_type_code, ZH_WORDS_GETTER("dictionary.library.code.summary"));
	//库位类型名称
	API_DTO_FIELD_DEFAULT(String, bin_type_name, ZH_WORDS_GETTER("dictionary.library.type.summary"));
};


/**
 * 库位类型列表分页数据对象
 */
class LibraryPageDTO : public PageDTO<LibraryListDTO::Wrapper>
{
	DTO_INIT(LibraryPageDTO, PageDTO<LibraryListDTO::Wrapper>);
};


#include OATPP_CODEGEN_END(DTO)
