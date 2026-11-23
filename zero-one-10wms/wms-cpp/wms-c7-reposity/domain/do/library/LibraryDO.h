#pragma once
/*
 @Author: nanbowan
*/
#include "../DoInclude.h"

/**
 * 库位类型数据实体类
 */
class LibraryDO
{
	using datetime = string;
	// 唯一id
	CC_SYNTHESIZE(string, id, Id);
	// 创建人名称
	CC_SYNTHESIZE(string, create_name, CreateName);
	// 创建人登录名称
	CC_SYNTHESIZE(string, create_by, CreateBy);
	// 创建日期
	CC_SYNTHESIZE(datetime, create_date, CreateDate);
	// 更新人名称
	CC_SYNTHESIZE(string, update_name, UpdateName);
	// 更新人登录名称
	CC_SYNTHESIZE(string, update_by, UpdateBy);
	// 更新日期
	CC_SYNTHESIZE(datetime, update_date, UpdateDate);
	// 所属部门
	CC_SYNTHESIZE(string, sys_org_code, SysOrgCode);
	// 所属公司
	CC_SYNTHESIZE(string, sys_company_code, SysCompanyCode);
	// 库位类型代码
	CC_SYNTHESIZE(string, bin_type_code, Code);
	// 库位类型名称
	CC_SYNTHESIZE(string, bin_type_name, Name);

public:
	LibraryDO() {
		id = "0";
		create_name = "";
		create_by = "";
		create_date = "";
		update_name = "";
		update_by = "";
		update_date = "";
		sys_org_code = "";
		sys_company_code = "";
		bin_type_code = "";
		bin_type_name = "";
	}
};

// 库位类型DO对象的指针类型设定，通常由智能指针使用
typedef std::shared_ptr<LibraryDO> PtrLibraryDO;

/*
* 库位类型表-库位类型名称（唯一标识 + 代码 + 名称）
*/
class LibraryNameDO
{
	// 唯一id
	CC_SYNTHESIZE(string, id, Id);
	// 库位类型代码
	CC_SYNTHESIZE(string, bin_type_code, Code);
	// 库位类型名称
	CC_SYNTHESIZE(string, bin_type_name, Name);

public:
	LibraryNameDO() {
		id = "";
		bin_type_code = "";
		bin_type_name = "";
	}
};

// 库位类型名称DO对象的指针类型设定
typedef std::shared_ptr<LibraryNameDO> PtrLibraryNameDO;


