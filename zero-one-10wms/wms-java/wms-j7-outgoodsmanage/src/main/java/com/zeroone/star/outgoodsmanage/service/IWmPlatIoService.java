package com.zeroone.star.outgoodsmanage.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.zeroone.star.outgoodsmanage.entity.WmPlatIo;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j7.outbound.WmPlatIoDTO;
import com.zeroone.star.project.query.j7.outbound.WmPlatIoQuery;

/**
 * <p>
 * 月台计划 服务类
 * </p>
 *
 * @author lenyan
 * @since 2025-02-21
 */
public interface IWmPlatIoService extends IService<WmPlatIo> {

    /**
     * 分页条件查询月台计划
     * @param query 查询条件
     * @return 分页数据
     */
    PageDTO<WmPlatIoDTO> listPlatIo(WmPlatIoQuery query);

    /**
     * 新增月台计划
     * @param dto 月台计划数据
     * @return 新增后的数据（含id）
     */
    WmPlatIoDTO addPlatIo(WmPlatIoDTO dto);

    /**
     * 修改月台计划
     * @param dto 月台计划数据（含id）
     * @return 修改后的数据
     */
    WmPlatIoDTO updatePlatIo(WmPlatIoDTO dto);
}
