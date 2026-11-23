package com.zeroone.star.stockln.controller;

import cn.hutool.core.bean.BeanUtil;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.stockln.WvStockDTO;
import com.zeroone.star.project.dto.j6.stockln.export.StockExportDTO;
import com.zeroone.star.project.j6.stockln.StockQueryApis;
import com.zeroone.star.project.query.j6.stockln.WvStockQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.stockln.service.IWvStockService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

@Api(tags = "库存查询")
@RestController
@RequestMapping("/stock/inventory-query")
public class StockQueryController implements StockQueryApis {

    @Resource
    private IWvStockService service;

    @Resource
    private EasyExcelComponent excel;

    @GetMapping("query-all")
    @ApiOperation(value = "分页查询库存接口")
    @Override
    public JsonVO<PageDTO<WvStockDTO>> queryAllStock(WvStockQuery condition) {
        return JsonVO.success(service.listallStock(condition));
    }

    @ApiOperation(value = "导出库存报表")
    @GetMapping("export")
    public ResponseEntity<byte[]> exportExcel(WvStockQuery condition) {
        List<WvStockDTO> list = service.listAllForExport(condition);
        List<StockExportDTO> data = new ArrayList<>();
        for (WvStockDTO item : list) {
            data.add(BeanUtil.copyProperties(item, StockExportDTO.class));
        }
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try {
            excel.export("库存查询", out, StockExportDTO.class, data);
        } catch (Exception e) {
            throw new RuntimeException("导出库存报表失败", e);
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"));
        headers.setContentDisposition(ContentDisposition.builder("attachment")
                .filename("库存查询.xlsx", StandardCharsets.UTF_8)
                .build());
        return ResponseEntity.ok().headers(headers).body(out.toByteArray());
    }
}
