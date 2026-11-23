package com.zeroone.star.project.j7.outbound;

import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j7.outbound.WmPlatIoDTO;
import com.zeroone.star.project.query.j7.outbound.WmPlatIoQuery;
import com.zeroone.star.project.vo.JsonVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.web.bind.annotation.*;

/**
 * <p>
 * 月台计划管理接口
 * </p>
 *
 * @author dev-yuetaiguanli
 * @since 2026-11-22
 */
@Api(tags = "月台计划管理")
public interface WmPlatIoApis {

    /**
     * 分页条件查询月台计划
     * @param query 查询条件
     * @return 分页数据
     */
    @ApiOperation("获取月台计划列表（条件+分页）")
    @GetMapping("/plat-io/list")
    JsonVO<PageDTO<WmPlatIoDTO>> listPlatIo(@ModelAttribute WmPlatIoQuery query);

    /**
     * 新增月台计划
     * @param dto 月台计划数据
     * @return 新增后数据（含id）
     */
    @ApiOperation("录入月台计划")
    @PostMapping("/plat-io")
    JsonVO<WmPlatIoDTO> addPlatIo(@RequestBody WmPlatIoDTO dto);

    /**
     * 修改月台计划
     * @param dto 月台计划数据（含id）
     * @return 修改后数据
     */
    @ApiOperation("修改月台计划")
    @PutMapping("/plat-io")
    JsonVO<WmPlatIoDTO> updatePlatIo(@RequestBody WmPlatIoDTO dto);
}
