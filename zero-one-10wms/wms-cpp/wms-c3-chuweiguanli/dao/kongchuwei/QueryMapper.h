#pragma once
#ifndef _QUERY_MAPPER_
#define _QUERY_MAPPER_

#include "Mapper.h"
#include "../../domain/do/BinDO.h"

/**
 * Ê¾Àý±í×Ö¶ÎÆ¥ÅäÓ³Éä
 */
class QueryMapper : public Mapper<BinDO>
{
public:
	BinDO mapper(ResultSet* resultSet) const override
	{
		BinDO data;
		data.setBinStore(resultSet->getString(1));
		data.setKuWeiShuXing(resultSet->getString(2));
		data.setCHPShuXing(resultSet->getString(3));
		data.setKuWeiBianMa(resultSet->getString(4));
		data.setSuoShuKeHu(resultSet->getString(5));
		data.setZuiDaTiJi(resultSet->getString(6));
		data.setShangJiaCiXu(resultSet->getString(7));
		data.setChang(resultSet->getString(8));
		data.setKuan(resultSet->getString(9));
		data.setGao(resultSet->getString(10));
		data.setZuiDaTuoPan(resultSet->getString(11));
		data.setTingYong(resultSet->getString(12));
		data.setKuWeiLeiXing(resultSet->getString(13));
		return data;
	}
};




// mapper for the empty-bin list query (id + all display columns)
class KongChuWeiMapper : public Mapper<BinDO>
{
public:
	BinDO mapper(ResultSet* resultSet) const override
	{
		BinDO data;
		data.setId(resultSet->getString(1));
		data.setBinStore(resultSet->getString(2));
		data.setKuWeiShuXing(resultSet->getString(3));
		data.setCHPShuXing(resultSet->getString(4));
		data.setKuWeiBianMa(resultSet->getString(5));
		data.setSuoShuKeHu(resultSet->getString(6));
		data.setZuiDaTiJi(resultSet->getString(7));
		data.setShangJiaCiXu(resultSet->getString(8));
		data.setChang(resultSet->getString(9));
		data.setKuan(resultSet->getString(10));
		data.setGao(resultSet->getString(11));
		data.setZuiDaTuoPan(resultSet->getString(12));
		data.setTingYong(resultSet->getString(13));
		data.setKuWeiLeiXing(resultSet->getString(14));
		return data;
	}
};

#endif // !_QUERY_MAPPER_