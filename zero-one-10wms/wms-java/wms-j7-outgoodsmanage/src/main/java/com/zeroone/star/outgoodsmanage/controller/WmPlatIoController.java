package com.zeroone.star.outgoodsmanage.controller;

import com.zeroone.star.outgoodsmanage.service.IWmPlatIoService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j7.outbound.WmPlatIoDTO;
import com.zeroone.star.project.j7.outbound.WmPlatIoApis;
import com.zeroone.star.project.query.j7.outbound.WmPlatIoQuery;
import com.zeroone.star.project.vo.JsonVO;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;

/**
 * <p>
 * 月台计划管理控制器
 * </p>
 *
 * @author dev-yuetaiguanli
 * @since 2026-11-22
 */
@RestController
@Validated
@Slf4j
public class WmPlatIoController implements WmPlatIoApis {

    @Resource
    private IWmPlatIoService wmPlatIoService;

    @Override
    @ApiOperation("获取月台计划列表（条件+分页）")
    public JsonVO<PageDTO<WmPlatIoDTO>> listPlatIo(WmPlatIoQuery query) {
        return JsonVO.success(wmPlatIoService.listPlatIo(query));
    }

    @Override
    @ApiOperation("录入月台计划")
    public JsonVO<WmPlatIoDTO> addPlatIo(WmPlatIoDTO dto) {
        try {
            return JsonVO.success(wmPlatIoService.addPlatIo(dto));
        } catch (IllegalArgumentException e) {
            log.warn("新增月台计划失败: {}", e.getMessage());
            return JsonVO.fail((WmPlatIoDTO) null);
        }
    }

    @Override
    @ApiOperation("修改月台计划")
    public JsonVO<WmPlatIoDTO> updatePlatIo(WmPlatIoDTO dto) {
        try {
            return JsonVO.success(wmPlatIoService.updatePlatIo(dto));
        } catch (IllegalArgumentException e) {
            log.warn("修改月台计划失败: {}", e.getMessage());
            return JsonVO.fail((WmPlatIoDTO) null);
        }
    }
}
