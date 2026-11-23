#include "stdafx.h"
#include "InventorylistDAO.h"
#include "InventorylistMapper.h"
#include <sstream>

// 内部工具函数前置声明（定义在本文件末尾）
static std::string getCurrentTimeAsString();

/*
 * 查询条件构造器：数据源为库存视图 wv_stock_stt（与动碰盘点同源）
 * 查询参数与视图列的映射关系：
 *   yidongriqi(移动日期)  -> last_move
 *   cktype(库存类型)      -> kuctype
 *   chuwei(储位)            -> ku_wei_bian_ma
 *   tuopan(托盘)            -> bin_id
 *   huozhu(货主)            -> cus_code
 *   huozhumingcheng(货主名称)  -> zhong_wen_qch
 *   shangpinbianma(商品编码)    -> goods_id
 *   shangpinshuliang(商品数量)    -> goods_qua
 *   shangpinmincheng(商品名称)    -> shp_ming_cheng
 *   shengchanriqi(生产日期)      -> goods_pro_data
 */
inline std::string InventorylistDAO::queryConditionBuilder(const InventorylistQuery::Wrapper& query, SqlParams& params)
{
    stringstream sqlCondition;
    sqlCondition << " WHERE 1=1";
    // 移动日期
    if (query->yidongriqi)
    {
        sqlCondition << " AND `last_move` =?";
        SQLPARAMS_PUSH(params, "s", std::string, query->yidongriqi.getValue(""));
    }
    // 库存类型
    if (query->cktype)
    {
        sqlCondition << " AND `kuctype` =?";
        SQLPARAMS_PUSH(params, "s", std::string, query->cktype.getValue(""));
    }
    // 储位
    if (query->chuwei)
    {
        sqlCondition << " AND `ku_wei_bian_ma` =?";
        SQLPARAMS_PUSH(params, "s", std::string, query->chuwei.getValue(""));
    }
    // 托盘
    if (query->tuopan)
    {
        sqlCondition << " AND `bin_id` =?";
        SQLPARAMS_PUSH(params, "s", std::string, query->tuopan.getValue(""));
    }
    // 货主
    if (query->huozhu)
    {
        sqlCondition << " AND `cus_code` =?";
        SQLPARAMS_PUSH(params, "s", std::string, query->huozhu.getValue(""));
    }
    // 货主名称
    if (query->huozhumingcheng)
    {
        sqlCondition << " AND `zhong_wen_qch` =?";
        SQLPARAMS_PUSH(params, "s", std::string, query->huozhumingcheng.getValue(""));
    }
    // 商品编码
    if (query->shangpinbianma)
    {
        sqlCondition << " AND `goods_id` =?";
        SQLPARAMS_PUSH(params, "s", std::string, query->shangpinbianma.getValue(""));
    }
    // 商品数量
    if (query->shangpinshuliang)
    {
        sqlCondition << " AND `goods_qua` =?";
        SQLPARAMS_PUSH(params, "s", std::string, query->shangpinshuliang.getValue(""));
    }
    // 商品名称
    if (query->shangpinmincheng)
    {
        sqlCondition << " AND `shp_ming_cheng` LIKE CONCAT('%',?,'%')";
        SQLPARAMS_PUSH(params, "s", std::string, query->shangpinmincheng.getValue(""));
    }
    // 生产日期
    if (query->shengchanriqi)
    {
        sqlCondition << " AND `goods_pro_data` =?";
        SQLPARAMS_PUSH(params, "s", std::string, query->shengchanriqi.getValue(""));
    }
    return sqlCondition.str();
}
// 统计数据条数
uint64_t InventorylistDAO::count(const InventorylistQuery::Wrapper& query)
{
    SqlParams params;
    string sql = "SELECT COUNT(*) FROM wv_stock_stt";
    // 拼接查询条件
    sql += queryConditionBuilder(query, params);
    // 执行查询
    return sqlSession->executeQueryNumerical(sql, params);
}
// 分页查询数据 wv_stock_stt
std::list<InventorylistDo> InventorylistDAO::selectWithPage(const InventorylistQuery::Wrapper& query)
{
    SqlParams params;
    string sql = "SELECT * FROM wv_stock_stt";
    // 拼接查询条件
    sql += queryConditionBuilder(query, params);
    // 拼接分页参数
    sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
    // 执行查询
    InventorylistMapper mapper;
    return sqlSession->executeQuery<InventorylistDo>(sql, mapper, params);
}
// 查询数据---不分页
std::list<InventorylistDo> InventorylistDAO::selectWithConditions(const InventorylistQuery::Wrapper& query)
{
    SqlParams params;
    string sql = "SELECT * FROM wv_stock_stt";
    // 拼接查询条件
    sql += queryConditionBuilder(query, params);
    // 执行查询
    InventorylistMapper mapper;
    return sqlSession->executeQuery<InventorylistDo>(sql, mapper, params);
}
// 通过ID查询数据
PtrInventorylistDo InventorylistDAO::selectById(uint64_t id)
{
    return {};
}
// 新增数据
uint64_t InventorylistDAO::insert(const InventorylistDo& iObj)
{
    string sql = "INSERT INTO `wm_stt_in_goods` (`id`,create_name,create_by,create_date,sys_org_code,sys_company_code,bin_id,tin_id,goods_id,goods_name,goods_qua,base_unit,goods_pro_data,goods_batch,cus_name,cus_code,stt_sta,stt_id,stt_type) VALUES( ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? )";
    UuidFacade uf(1);
    return sqlSession->executeInsert(sql, "%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s", uf.genUuid(), iObj.getCreateName(), iObj.getCreateBy(), iObj.getCreateDate(), iObj.getSysOrgCode(), iObj.getSysCompanyCode(), iObj.getBinId(), iObj.getTinId(), iObj.getGoodsId(), iObj.getGoodsName(), iObj.getGoodsQua(), iObj.getBaseUnit(), iObj.getGoodsProDate(), iObj.getGoodsBatch(), iObj.getCusName(), iObj.getCusCode(), iObj.getSttSta(), iObj.getSttId(), iObj.getSttType());
}
// 修改盘点任务：动态拼接已传字段，并补全审计字段
int InventorylistDAO::updateById(const InventorylistDo& uObj, const PayloadDTO& payload)
{
    stringstream sqlCondition;
    SqlParams params;
    sqlCondition << " SET `update_name` = ?, `update_by` = ?, `update_date` = ?";
    SQLPARAMS_PUSH(params, "s", std::string, payload.getRealname());
    SQLPARAMS_PUSH(params, "s", std::string, payload.getUsername());
    SQLPARAMS_PUSH(params, "s", std::string, getCurrentTimeAsString());
    if (uObj.getSttQua() != "")
    {
        sqlCondition << ", `stt_qua` = ?";
        SQLPARAMS_PUSH(params, "s", std::string, uObj.getSttQua());
    }
    if (uObj.getGoodsQua() != "")
    {
        sqlCondition << ", `goods_qua` = ?";
        SQLPARAMS_PUSH(params, "s", std::string, uObj.getGoodsQua());
    }
    if (uObj.getGoodsBatch() != "")
    {
        sqlCondition << ", `goods_batch` = ?";
        SQLPARAMS_PUSH(params, "s", std::string, uObj.getGoodsBatch());
    }
    if (uObj.getGoodsProDate() != "")
    {
        sqlCondition << ", `goods_pro_data` = ?";
        SQLPARAMS_PUSH(params, "s", std::string, uObj.getGoodsProDate());
    }
    if (uObj.getBinId() != "")
    {
        sqlCondition << ", `bin_id` = ?";
        SQLPARAMS_PUSH(params, "s", std::string, uObj.getBinId());
    }
    if (uObj.getTinId() != "")
    {
        sqlCondition << ", `tin_id` = ?";
        SQLPARAMS_PUSH(params, "s", std::string, uObj.getTinId());
    }
    if (uObj.getSttSta() != "")
    {
        sqlCondition << ", `stt_sta` = ?";
        SQLPARAMS_PUSH(params, "s", std::string, uObj.getSttSta());
    }
    string sql = "UPDATE `wm_stt_in_goods`" + sqlCondition.str() + " WHERE `id` = ?";
    SQLPARAMS_PUSH(params, "s", std::string, uObj.getId());
    return sqlSession->executeUpdate(sql, params);
}
// 旧版修改（已由 updateById 替代，保留以兼容未更新的调用方）
int InventorylistDAO::update(const InventorylistDo& uObj)
{
    return 0;
}
// 获取当前时间字符串（文件内部工具函数）
static std::string getCurrentTimeAsString() {
	auto now = std::chrono::system_clock::now();
	std::time_t now_c = std::chrono::system_clock::to_time_t(now);
	std::tm* now_tm = std::localtime(&now_c);

	char buffer[80];
	std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", now_tm);
	return std::string(buffer);
}
