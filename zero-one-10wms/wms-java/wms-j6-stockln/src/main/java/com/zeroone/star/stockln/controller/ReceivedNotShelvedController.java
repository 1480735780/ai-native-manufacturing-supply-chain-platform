package com.zeroone.star.stockln.controller;

import cn.hutool.core.bean.BeanUtil;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.stockln.InboundQmIDTO;
import com.zeroone.star.project.dto.j6.stockln.export.ToShelvesExportDTO;
import com.zeroone.star.project.j6.stockln.ReceivedNotShelvedApis;
import com.zeroone.star.project.query.j6.stockln.ToShelvesQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.stockln.service.IToShelvesService;
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
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

@Api(tags = "收货上架")
@RestController
@RequestMapping("/stock/not-shelved")
public class ReceivedNotShelvedController implements ReceivedNotShelvedApis {

    private static final DateTimeFormatter DATE_TIME_FORMATTER =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Resource
    private IToShelvesService toShelvesService;

    @Resource
    private EasyExcelComponent easyExcelComponent;

    @GetMapping("/query-all")
    @ApiOperation("获取未上架货物列表（条件+分页）")
    public JsonVO<PageDTO<InboundQmIDTO>> queryAll(ToShelvesQuery query) {
        return JsonVO.success(toShelvesService.listNotShelved(query));
    }

    @GetMapping("/export")
    @ApiOperation("导出未上架货物")
    public ResponseEntity<byte[]> export(ToShelvesQuery query) {
        List<InboundQmIDTO> list = toShelvesService.listNotShelvedForExport(query);
        List<ToShelvesExportDTO> data = new ArrayList<>();
        for (InboundQmIDTO item : list) {
            ToShelvesExportDTO dto = BeanUtil.copyProperties(item, ToShelvesExportDTO.class);
            dto.setCreateDate(item.getCreateDate() == null ? "" : item.getCreateDate().format(DATE_TIME_FORMATTER));
            data.add(dto);
        }
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try {
            easyExcelComponent.export("收货上架", out, ToShelvesExportDTO.class, data);
        } catch (Exception e) {
            throw new RuntimeException("导出收货上架失败", e);
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"));
        headers.setContentDisposition(ContentDisposition.builder("attachment")
                .filename("收货上架.xlsx", StandardCharsets.UTF_8)
                .build());
        return ResponseEntity.ok().headers(headers).body(out.toByteArray());
    }
}
