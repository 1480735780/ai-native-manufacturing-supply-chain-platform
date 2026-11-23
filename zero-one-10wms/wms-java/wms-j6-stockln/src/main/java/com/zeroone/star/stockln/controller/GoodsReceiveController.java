package com.zeroone.star.stockln.controller;
import cn.hutool.core.bean.BeanUtil;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.dto.j6.stockln.BatchModifyBinDTO;
import com.zeroone.star.project.dto.j6.stockln.BatchUpdateProductionDateDTO;
import com.zeroone.star.project.dto.j6.stockln.BatchUpdateShelfDTO;
import com.zeroone.star.project.dto.j6.stockln.ModifyShelvesDTO;
import lombok.extern.slf4j.Slf4j;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.stockln.InboundQmIDTO;
import com.zeroone.star.project.dto.j6.stockln.ToShelvesDTO;
import com.zeroone.star.project.dto.j6.stockln.export.ToShelvesExportDTO;
import com.zeroone.star.project.dto.j6.stockln.export.ToShelvesImportDTO;
import com.zeroone.star.project.j6.stockln.GoodsReceiveApis;
import com.zeroone.star.project.query.j6.stockln.ToShelvesQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.stockln.service.IToShelvesService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import javax.validation.Valid;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

@Api(tags = "收货登记")
@RestController
@RequestMapping("/stock/good-receive")
@Validated
@Slf4j
public class GoodsReceiveController implements GoodsReceiveApis {

    @Resource
    IToShelvesService iToShelvesService;

    @Resource
    EasyExcelComponent easyExcelComponent;

    private static final DateTimeFormatter DATE_TIME_FORMATTER =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    /**
     * 待上架货物列表分页查询
     *
     * @param
     * @return
     */
    @GetMapping("/query-all")
    @ApiOperation("待上架货物列表分页查询")
    public JsonVO<PageDTO<InboundQmIDTO>> pageToSheleves(ToShelvesQuery toShelvesQuery) {
        PageDTO<InboundQmIDTO> pageDTO = iToShelvesService.listall(toShelvesQuery);
        return JsonVO.success(pageDTO);
    }

    /**
     * 待上架货物详细信息查询
     *
     * @param
     * @return
     */
    @GetMapping("/{id}")
    @ApiOperation("待上架货物详细信息查询")
    public JsonVO<InboundQmIDTO> getShelevesByid(@PathVariable String id) {
        InboundQmIDTO dto = iToShelvesService.myGetById(id);
        return JsonVO.success(dto);
    }

    @ApiOperation(value = "录入待上架货物")
    @PostMapping("/addItem")
    public JsonVO<String> addItem(@RequestBody @Valid ToShelvesDTO dto) {
        log.info("收到前端请求，录入待上架货物: {}", dto);
        iToShelvesService.insertItem(dto);
        return JsonVO.success("添加成功");
    }

    @ApiOperation(value = "删除待上架货物")
    @DeleteMapping("/{id}")
    public JsonVO<String> removeItem(@PathVariable String id) {

        if (iToShelvesService.deleteById(id)) {
            return JsonVO.success("删除成功");
        }
        return JsonVO.fail("删除失败");
    }

    @ApiOperation(value = "修改待上架货物信息")
    @PostMapping("/modifyItem")
    public JsonVO<String> modifyItem(@RequestBody ModifyShelvesDTO dto) {
        // 调用 Service 层的方法进行修改操作
        iToShelvesService.modifyShelvesInfo(dto);
        return JsonVO.success("修改成功");
    }

    @ApiOperation(value = "批量修改储位")
    @PostMapping("/batchModifyBin")
    public JsonVO<String> batchModifyBin(@RequestBody BatchModifyBinDTO dto) {
        // 调用 Service 层的方法进行批量修改储位操作
        boolean result = iToShelvesService.batchModifyBin(dto.getIds(), dto.getBinId());

        // 根据操作结果返回相应的响应
        if (result) {
            return JsonVO.success("批量修改储位成功");
        } else {
            return JsonVO.fail("批量修改储位失败");
        }
    }

    @ApiOperation(value = "批量修改生产日期")
    @PostMapping("/batchModifyProductionDate")
    public JsonVO<String> batchModifyProductionDate(@RequestBody BatchUpdateProductionDateDTO dto) {
        if (dto.getIds() == null || dto.getIds().isEmpty()) {
            return JsonVO.fail("货物ID列表不能为空");
        }
        boolean result = iToShelvesService.batchModifyProductionDate(dto.getIds(), dto.getNewProductionDate());
        return result ? JsonVO.success("批量修改生产日期成功") : JsonVO.fail("批量修改生产日期失败");
    }

    @ApiOperation(value = "上架货物（支持批量上架）")
    @PostMapping("/batchShelf")
    public JsonVO<String> batchShelf(@RequestBody BatchUpdateShelfDTO dto) {
        if (dto.getIds() == null || dto.getIds().isEmpty()) {
            return JsonVO.fail("货物ID列表不能为空");
        }
        int count = iToShelvesService.batchShelf(dto.getIds());
        return JsonVO.success("上架成功，共 " + count + " 条");
    }

    // 导入报表接口
    @ApiOperation(value = "Excel批量导入待上架货物")
    @PostMapping(value = "/importItems", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public JsonVO<String> importItems(
            @ApiParam(value = "Excel文件", required = true)
            @RequestParam("file") MultipartFile file) {
        List<ToShelvesImportDTO> rows = easyExcelComponent.parseExcel(file, ToShelvesImportDTO.class);
        List<ToShelvesDTO> items = new ArrayList<>();
        for (ToShelvesImportDTO row : rows) {
            items.add(BeanUtil.copyProperties(row, ToShelvesDTO.class));
        }
        int count = iToShelvesService.importItems(items);
        return JsonVO.success("导入成功，共 " + count + " 条");
    }

    @ApiOperation(value = "导出待上架货物报表")
    @GetMapping("/exportAllItems")
    public ResponseEntity<byte[]> exportAllItems(ToShelvesQuery query) {
        List<InboundQmIDTO> list = iToShelvesService.listAllForExport(query);
        List<ToShelvesExportDTO> data = new ArrayList<>();
        for (InboundQmIDTO item : list) {
            ToShelvesExportDTO dto = BeanUtil.copyProperties(item, ToShelvesExportDTO.class);
            dto.setCreateDate(item.getCreateDate() == null ? "" : item.getCreateDate().format(DATE_TIME_FORMATTER));
            data.add(dto);
        }
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try {
            easyExcelComponent.export("收货登记", out, ToShelvesExportDTO.class, data);
        } catch (Exception e) {
            throw new RuntimeException("导出收货登记失败", e);
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"));
        headers.setContentDisposition(ContentDisposition.builder("attachment")
                .filename("收货登记.xlsx", StandardCharsets.UTF_8)
                .build());
        return ResponseEntity.ok().headers(headers).body(out.toByteArray());
    }
}
