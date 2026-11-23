package com.zeroone.star.stockln.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.stockln.InboundQmIDTO;
import com.zeroone.star.project.dto.j6.stockln.ModifyShelvesDTO;
import com.zeroone.star.project.dto.j6.stockln.ToShelvesDTO;
import com.zeroone.star.project.query.j6.stockln.ToShelvesQuery;
import com.zeroone.star.stockln.entity.ToShelves;

import java.util.List;

/**
 * 待上架服务类
 */
public interface IToShelvesService extends IService<ToShelves> {
    PageDTO<InboundQmIDTO> listall(ToShelvesQuery toShelvesQuery);

    void insertItem(ToShelvesDTO dto);

    boolean deleteById(String id);

    /**
     * 修改待上架货物信息
     *
     * @param dto 包含待上架货物修改信息的 DTO
     * @return 修改是否成功
     */
    boolean modifyShelvesInfo(ModifyShelvesDTO dto);

    boolean batchModifyBin(List<String> ids, String binId);

    /**
     * 批量修改生产日期
     *
     * @param ids    货物ID列表
     * @param proData 新的生产日期
     * @return 是否成功
     */
    boolean batchModifyProductionDate(List<String> ids, String proData);

    /**
     * 批量上架：更新待上架状态并写入库存上架记录
     *
     * @param ids 货物ID列表
     * @return 成功条数
     */
    int batchShelf(List<String> ids);

    /**
     * Excel 导入待上架货物
     *
     * @param items 导入数据
     * @return 成功条数
     */
    int importItems(List<ToShelvesDTO> items);

    /**
     * 导出用列表
     *
     * @param query 查询条件
     * @return 列表
     */
    List<InboundQmIDTO> listAllForExport(ToShelvesQuery query);

    /**
     * 收货上架：查询未上架货物
     */
    PageDTO<InboundQmIDTO> listNotShelved(ToShelvesQuery query);

    /**
     * 收货上架：导出未上架货物
     */
    List<InboundQmIDTO> listNotShelvedForExport(ToShelvesQuery query);

    InboundQmIDTO myGetById(String id);
}
