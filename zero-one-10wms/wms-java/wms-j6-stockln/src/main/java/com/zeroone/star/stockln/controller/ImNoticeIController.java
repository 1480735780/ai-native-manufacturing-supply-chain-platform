package com.zeroone.star.stockln.controller;

import com.zeroone.star.project.j6.stockln.InNoticeApis;
import com.zeroone.star.project.query.j6.stockln.InNoticeQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.project.vo.j6.stockln.InNoticePageVO;
import com.zeroone.star.stockln.service.InNoticeService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import java.nio.charset.StandardCharsets;

@Api(tags = "进货通知明细")
@RestController
@RequestMapping("/stock/imNotice-detail")
public class ImNoticeIController implements InNoticeApis {

    private static final MediaType EXCEL_MEDIA_TYPE =
            MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

    @Resource
    private InNoticeService inNoticeService;

    @Override
    @GetMapping("/items")
    @ApiOperation("获取入库通知单明细列表（条件+分页）")
    public JsonVO<InNoticePageVO> getInNoticeItems(InNoticeQuery query,
                                                   @RequestParam(defaultValue = "0") int page,
                                                   @RequestParam(defaultValue = "0") int size) {
        return JsonVO.success(inNoticeService.getInNoticeItems(query, page, size));
    }

    @GetMapping("/export")
    @ApiOperation("导出进货通知明细")
    public ResponseEntity<byte[]> export(InNoticeQuery query) {
        byte[] content = inNoticeService.exportInNotice(query);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(EXCEL_MEDIA_TYPE);
        headers.setContentDisposition(ContentDisposition.builder("attachment")
                .filename("进货通知明细.xlsx", StandardCharsets.UTF_8)
                .build());
        return ResponseEntity.ok().headers(headers).body(content);
    }
}
