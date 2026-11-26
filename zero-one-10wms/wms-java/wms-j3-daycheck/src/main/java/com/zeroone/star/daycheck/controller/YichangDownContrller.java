package com.zeroone.star.daycheck.controller;

import cn.hutool.core.date.DateTime;
import com.zeroone.star.daycheck.entity.YichangDown;
import com.zeroone.star.daycheck.service.YichangDownService;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.daycheck.Arr.YichangDownDTO;
import com.zeroone.star.project.j3.daycheck.YichangDownApis;
import com.zeroone.star.project.query.j3.daycheck.Arr.YichangDownQuery;
import com.zeroone.star.project.vo.JsonVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.SneakyThrows;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseBody;

import javax.annotation.Resource;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * @author aaa
 * @version 1.0
 * @description TODO
 * @date 2025/2/22 14:12
 */
@Controller
@RequestMapping("/daycheck/yi-chang")
@Api(tags = "出货异常")
@Validated
public class YichangDownContrller implements YichangDownApis {

    @Resource
    YichangDownService yichangDownService;

    @Resource
    EasyExcelComponent excel;

    @GetMapping("/get-yichang-down")
    @ResponseBody
    @ApiOperation(value = "获取出库异常")
    @Override
    public JsonVO<List<YichangDownDTO>> getYichangDown(YichangDownQuery condition) {
        if (condition.getSort() != null && !condition.getSort().isEmpty()
                && !"oldest".equals(condition.getSort())) {
            return JsonVO.create(null, 9995, "sort 仅支持 oldest");
        }
        List<YichangDownDTO> yichangList =  yichangDownService.getYichangDownPage(condition);
        return JsonVO.success(yichangList);
    }

    @GetMapping("/get-yichang-down-page")
    @ResponseBody
    @ApiOperation(value = "获取出货异常（巡检分页：rows/total/pages）")
    @Override
    public JsonVO<PageDTO<YichangDownDTO>> getYichangDownPaged(YichangDownQuery condition) {
        if (condition.getSort() != null && !condition.getSort().isEmpty()
                && !"oldest".equals(condition.getSort())) {
            return JsonVO.create(null, 9995, "sort 仅支持 oldest");
        }
        return JsonVO.success(yichangDownService.getYichangDownPageDTO(condition));
    }

    @SneakyThrows
    @GetMapping("/download")
    @ApiOperation(value = "获取当前条件下的数据excel")
    @Override
    public ResponseEntity<byte[]> downLoadYicchang() {
        List<YichangDown> data;
        try {
            data = yichangDownService.getYichangDownDate();
        } catch (IllegalStateException ex) {
            // 导出超限或翻页期间数据变更：明确失败，绝不返回一份缺数/重复的 Excel。
            return ResponseEntity.status(HttpStatus.CONFLICT)
                    .contentType(MediaType.TEXT_PLAIN)
                    .body(ex.getMessage().getBytes(StandardCharsets.UTF_8));
        }
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        excel.export("sheet1",out,YichangDown.class,data);
        String fileName = "excel--" + DateTime.now().toString("yyyyMMdd") + ".xlsx";
        HttpHeaders httpHeaders = new HttpHeaders();
        httpHeaders.setContentDispositionFormData("attachment", fileName);
        httpHeaders.setContentType(MediaType.APPLICATION_OCTET_STREAM);
        ResponseEntity<byte[]> result = new ResponseEntity<>(out.toByteArray(), httpHeaders, HttpStatus.CREATED);
        out.close();
        return result;
    }
}
