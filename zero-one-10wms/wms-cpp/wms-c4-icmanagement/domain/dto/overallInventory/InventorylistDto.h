#pragma once
#ifndef _INVENTORYLIST_DTO_
#define _INVENTORYLIST_DTO_

#include "../../GlobalInclude.h"
#include "domain/query/PageQuery.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 示例分页查询数据
 */
class InventoryBaseDTO : public oatpp::DTO
{
	DTO_INIT(InventoryBaseDTO, DTO);
	// 移动日期
	API_DTO_FIELD_DEFAULT(String, yidongriqi, ZH_WORDS_GETTER("overall.inventorylist.yidongriqi"));
	// 库存类型
	API_DTO_FIELD_DEFAULT(String, cktype, ZH_WORDS_GETTER("overall.inventorylist.cktype"));
	// 储位
	API_DTO_FIELD_DEFAULT(String, chuwei, ZH_WORDS_GETTER("overall.inventorylist.chuwei"));
	// 托盘
	API_DTO_FIELD_DEFAULT(String, tuopan, ZH_WORDS_GETTER("overall.inventorylist.tuopan"));
	// 货主
	API_DTO_FIELD_DEFAULT(String, huozhu, ZH_WORDS_GETTER("overall.inventorylist.huozhu"));
	// 货主名称
	API_DTO_FIELD_DEFAULT(String, huozhumingcheng, ZH_WORDS_GETTER("overall.inventorylist.huozhumingcheng"));
	// 商品编码
	API_DTO_FIELD_DEFAULT(String, shangpinbianma, ZH_WORDS_GETTER("overall.inventorylist.shangpinbianma"));
	// 商品数量
	API_DTO_FIELD_DEFAULT(String, shangpinshuliang, ZH_WORDS_GETTER("overall.inventorylist.shangpinshuliang"));
	// 商品名称
	API_DTO_FIELD_DEFAULT(String, shangpinmincheng, ZH_WORDS_GETTER("overall.inventorylist.shangpinmincheng"));
	// 生产日期
	API_DTO_FIELD_DEFAULT(String, shengchanriqi, ZH_WORDS_GETTER("overall.inventorylist.shengchanriqi"));
};

class InventoryAddDTO : public InventoryBaseDTO
{
	DTO_INIT(InventoryAddDTO, InventoryBaseDTO);
	// 移动日期
	API_DTO_FIELD_DEFAULT(String, yidongriqi, ZH_WORDS_GETTER("overall.inventorylist.yidongriqi"));
	// 库存类型
	API_DTO_FIELD_DEFAULT(String, cktype, ZH_WORDS_GETTER("overall.inventorylist.cktype"));
	// 储位
	API_DTO_FIELD_DEFAULT(String, chuwei, ZH_WORDS_GETTER("overall.inventorylist.chuwei"));
	// 托盘
	API_DTO_FIELD_DEFAULT(String, tuopan, ZH_WORDS_GETTER("overall.inventorylist.tuopan"));
	// 货主
	API_DTO_FIELD_DEFAULT(String, huozhu, ZH_WORDS_GETTER("overall.inventorylist.huozhu"));
	// 货主名称
	API_DTO_FIELD_DEFAULT(String, huozhumingcheng, ZH_WORDS_GETTER("overall.inventorylist.huozhumingcheng"));
	// 商品编码
	API_DTO_FIELD_DEFAULT(String, shangpinbianma, ZH_WORDS_GETTER("overall.inventorylist.shangpinbianma"));
	// 商品数量
	API_DTO_FIELD_DEFAULT(String, shangpinshuliang, ZH_WORDS_GETTER("overall.inventorylist.shangpinshuliang"));
	// 商品名称
	API_DTO_FIELD_DEFAULT(String, shangpinmincheng, ZH_WORDS_GETTER("overall.inventorylist.shangpinmincheng"));
	// 生产日期
	API_DTO_FIELD_DEFAULT(String, shengchanriqi, ZH_WORDS_GETTER("overall.inventorylist.shengchanriqi"));
};

/**
 * 盘点人详细数据列表
 */
class InventoryDtailDTO : public InventoryAddDTO
{
	DTO_INIT(InventoryDtailDTO, InventoryAddDTO);
	// 移动日期
	API_DTO_FIELD_DEFAULT(String, yidongriqi, ZH_WORDS_GETTER("overall.inventorylist.yidongriqi"));
	// 库存类型
	API_DTO_FIELD_DEFAULT(String, cktype, ZH_WORDS_GETTER("overall.inventorylist.cktype"));
	// 储位
	API_DTO_FIELD_DEFAULT(String, chuwei, ZH_WORDS_GETTER("overall.inventorylist.chuwei"));
	// 托盘
	API_DTO_FIELD_DEFAULT(String, tuopan, ZH_WORDS_GETTER("overall.inventorylist.tuopan"));
	// 货主
	API_DTO_FIELD_DEFAULT(String, huozhu, ZH_WORDS_GETTER("overall.inventorylist.huozhu"));
	// 货主名称
	API_DTO_FIELD_DEFAULT(String, huozhumingcheng, ZH_WORDS_GETTER("overall.inventorylist.huozhumingcheng"));
	// 商品编码
	API_DTO_FIELD_DEFAULT(String, shangpinbianma, ZH_WORDS_GETTER("overall.inventorylist.shangpinbianma"));
	// 商品数量
	API_DTO_FIELD_DEFAULT(String, shangpinshuliang, ZH_WORDS_GETTER("overall.inventorylist.shangpinshuliang"));
	// 商品名称
	API_DTO_FIELD_DEFAULT(String, shangpinmincheng, ZH_WORDS_GETTER("overall.inventorylist.shangpinmincheng"));
	// 生产日期
	API_DTO_FIELD_DEFAULT(String, shengchanriqi, ZH_WORDS_GETTER("overall.inventorylist.shengchanriqi"));
};

/**
 * 盘点人列表分页对象
 */
class InventorylistDto : public PageDTO<InventoryBaseDTO::Wrapper>
{
	DTO_INIT(InventorylistDto, PageDTO<InventoryBaseDTO::Wrapper>);
};

/*
* DTO for batch stocktake task generation: receives id array, also returns succeeded ids
*/
class InventoryInsertTaskDTO : public oatpp::DTO
{
	DTO_INIT(InventoryInsertTaskDTO, DTO);

	API_DTO_FIELD_DEFAULT(Vector<String>, ids, ZH_WORDS_GETTER("sttOnMove.field.ids"));
};

/*
* DTO for editing a stocktake task: id required, other fields optional
*/
class InventoryModifyDTO : public oatpp::DTO
{
	DTO_INIT(InventoryModifyDTO, DTO);

	API_DTO_FIELD(String, id, ZH_WORDS_GETTER("sttTask.field.id"), true, "");
	API_DTO_FIELD_DEFAULT(String, stt_qua, ZH_WORDS_GETTER("mql.stt.stt_qua"));
	API_DTO_FIELD_DEFAULT(String, goods_qua, ZH_WORDS_GETTER("mql.goods.goods_qua"));
	API_DTO_FIELD_DEFAULT(String, goods_batch, ZH_WORDS_GETTER("mql.goods.goods_batch"));
	API_DTO_FIELD_DEFAULT(String, goods_pro_data, ZH_WORDS_GETTER("mql.goods.goods_pro_data"));
	API_DTO_FIELD_DEFAULT(String, bin_id, ZH_WORDS_GETTER("mql.rest.bin_id"));
	API_DTO_FIELD_DEFAULT(String, tin_id, ZH_WORDS_GETTER("mql.rest.tin_id"));
	API_DTO_FIELD_DEFAULT(String, stt_sta, ZH_WORDS_GETTER("mql.stt.stt_sta"));
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_SAMPLE_QUERY_