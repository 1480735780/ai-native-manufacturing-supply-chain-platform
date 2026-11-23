#pragma once
#ifndef _INVENTORY_LIST_MAPER_
#define _INVENTORY_LIST_MAPER_
#include "Mapper.h"
#include "../../domain/do/overallInventory/InventorylistDo.h"
/**
 * 库存视图 wv_stock_stt 字段映射（列序与视图定义一致）
 * create_date, create_name, create_by, id, kuctype, ku_wei_bian_ma, bin_id,
 * cus_code, zhong_wen_qch, goods_code, goods_id, goods_qua, shp_ming_cheng,
 * goods_pro_data, bzhi_qi, yushoutianshu, goods_unit
 * 页面语义映射：储位->bin_id 托盘->tin_id 盘点数量->stt_qua 盘点类型->stt_type
 */
class InventorylistMapper : public Mapper<InventorylistDo>
{
public:
	InventorylistDo mapper(ResultSet* resultSet) const override
	{
		InventorylistDo data;
		data.setCreateDate(resultSet->getString(1));     // create_date 创建日期(移动日期)
		data.setCreateName(resultSet->getString(2));     // create_name
		data.setCreateBy(resultSet->getString(3));       // create_by
		data.setId(resultSet->getString(4));             // id
		data.setSttType(resultSet->getString(5));        // kuctype 库存类型(盘点类型)
		data.setBinId(resultSet->getString(6));          // ku_wei_bian_ma 储位
		data.setTinId(resultSet->getString(7));          // bin_id 托盘
		data.setCusCode(resultSet->getString(8));        // cus_code 货主
		data.setCusName(resultSet->getString(9));        // zhong_wen_qch 货主名称
		data.setGoodsCode(resultSet->getString(10));     // goods_code
		data.setGoodsId(resultSet->getString(11));       // goods_id 商品编码
		data.setSttQua(resultSet->getString(12));        // goods_qua 商品数量(盘点数量)
		data.setGoodsName(resultSet->getString(13));     // shp_ming_cheng 商品名称
		data.setGoodsProDate(resultSet->getString(14));  // goods_pro_data 生产日期
		data.setGoodsBatch(resultSet->getString(15));    // bzhi_qi 保质期(批次)
		data.setBaseUnit(resultSet->getString(17));      // goods_unit 单位
		return data;
	}
};
/**
 * 库存视图字段映射--返回智能指针版本
 */
class PtrSampleMapper : public Mapper<PtrInventorylistDo>
{
public:
	PtrInventorylistDo mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<InventorylistDo>();
		data->setCreateDate(resultSet->getString(1));
		data->setCreateName(resultSet->getString(2));
		data->setCreateBy(resultSet->getString(3));
		data->setId(resultSet->getString(4));
		data->setSttType(resultSet->getString(5));
		data->setBinId(resultSet->getString(6));
		data->setTinId(resultSet->getString(7));
		data->setCusCode(resultSet->getString(8));
		data->setCusName(resultSet->getString(9));
		data->setGoodsCode(resultSet->getString(10));
		data->setGoodsId(resultSet->getString(11));
		data->setSttQua(resultSet->getString(12));
		data->setGoodsName(resultSet->getString(13));
		data->setGoodsProDate(resultSet->getString(14));
		data->setGoodsBatch(resultSet->getString(15));
		data->setBaseUnit(resultSet->getString(17));
		return data;
	}
};
#endif // !_INVENTORY_LIST_MAPER_
