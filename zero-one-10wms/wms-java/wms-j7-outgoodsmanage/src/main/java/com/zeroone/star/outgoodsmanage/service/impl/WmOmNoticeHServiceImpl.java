package com.zeroone.star.outgoodsmanage.service.impl;


import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.StrUtil;

import cn.hutool.core.lang.func.Func1;
import com.alibaba.excel.EasyExcel;
import com.alibaba.excel.ExcelWriter;
import com.alibaba.excel.write.builder.ExcelWriterBuilder;
import com.alibaba.excel.write.handler.WorkbookWriteHandler;
import com.alibaba.excel.write.metadata.WriteSheet;
import com.alibaba.excel.write.metadata.holder.WriteWorkbookHolder;
import com.alibaba.excel.write.style.HorizontalCellStyleStrategy;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.outgoodsmanage.entity.*;
import com.zeroone.star.outgoodsmanage.mapper.WmOmNoticeHMapper;
import com.zeroone.star.outgoodsmanage.mapper.WmOmNoticeIMapper;
import com.zeroone.star.outgoodsmanage.mapper.WmOmQmIMapper;
import com.zeroone.star.outgoodsmanage.service.IWmOmNoticeHService;
import com.zeroone.star.outgoodsmanage.util.ExcelStyleUtils;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.components.pdf.PdfComponent;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j7.outdetail.OutDetailDTO;
import com.zeroone.star.project.dto.j7.outmanage.OutNoticeItemDTO;
import com.zeroone.star.project.dto.j7.outmanage.OutNoticeListDTO;
import com.zeroone.star.project.dto.j7.outmanage.WonhDTO;
import com.zeroone.star.project.query.j7.outbound.WonQuery;
import com.zeroone.star.project.dto.j7.outdetail.OutDetailExcelDTO;
import com.zeroone.star.project.query.j7.outdetail.OutDetailExcelQuery;
import com.zeroone.star.project.query.j7.outdetail.OutDetailQuery;
import com.zeroone.star.project.query.j7.outnotice.OutGoodNoticeQuery;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.util.CellRangeAddress;
import org.mapstruct.Mapper;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

@Mapper(componentModel = "spring")
interface MsOutGoodsMapper{
    /**
     * 将OutDetailDO转换为OutDetailDTO
     * @param outDetailDO 转换原对象
     * @return 转换后的对象
     */
    OutDetailDTO outDetailDOTooutDetailDTO(OutDetailDO outDetailDO);

    OutNoticeListDTO wmOmNoticeHToOutNoticeListDTO(WmOmNoticeH wmOmNoticeH);
    OutDetailExcelDTO outDetailExcelDTooutDeTailExcelDTO(OutDetailExcelDO outDetailExcelDO);
}

@Mapper(componentModel = "spring")
interface  MsWonhMapper{
    WonhDTO WonhToWonhDTO(WmOmNoticeH wmOmNoticeH);
}
/**
 * <p>
 * 出库通知抬头 服务实现类
 * </p>
 *
 * @author lenyan
 * @since 2025-02-21
 */
@Service
public class WmOmNoticeHServiceImpl extends ServiceImpl<WmOmNoticeHMapper, WmOmNoticeH> implements IWmOmNoticeHService {

    @Resource
    private WmOmNoticeHMapper wmOmNoticeHMapper;


    @Resource
    private WmOmNoticeIMapper wmOmNoticeIMapper;

    @Resource
    private WmOmQmIMapper wmOmQmIMapper;

    @Resource
    MsOutGoodsMapper msMapper;

    @Resource
    MsWonhMapper msWonhMapper;

    @Resource
    PdfComponent pdfComponent;

    @Override
    @org.springframework.transaction.annotation.Transactional(rollbackFor = Exception.class)
    public Long removeNoticeH(String id) {
        if (StrUtil.isBlank(id)) {
            return 0L;
        }
        WmOmNoticeH head = wmOmNoticeHMapper.selectOne(new QueryWrapper<WmOmNoticeH>()
                .eq("om_notice_id", id));
        if (head == null) {
            head = wmOmNoticeHMapper.selectById(id);
        }
        if (head == null) {
            return 0L;
        }
        String noticeId = StrUtil.isNotBlank(head.getOmNoticeId()) ? head.getOmNoticeId() : id;
        int total = wmOmNoticeIMapper.delete(new QueryWrapper<WmOmNoticeI>()
                .eq("om_notice_id", noticeId));
        total += wmOmQmIMapper.delete(new QueryWrapper<WmOmQmI>()
                .eq("om_notice_id", noticeId));
        total += wmOmNoticeHMapper.deleteById(head.getId());
        return (long) total;
    }

    @Override
    public PageDTO<OutDetailDTO> listAll (OutDetailQuery query){
        //构建分页对象 不用mp 不用这个对象传参 否则会自动写分页语
        Page<OutDetailDO> page = new Page<>(query.getPageIndex(), query.getPageSize());

        int offset = (int) ((query.getPageIndex() - 1) * query.getPageSize());
        //这里分页查询方法返回值用list 不用page page对象是mp的对象 会自动写分页
        List<OutDetailDO> byPage = wmOmNoticeHMapper.getOrderDetailsByPage(query, (int) query.getPageSize(),offset);
        Page<OutDetailDO> page1 = new Page<>(query.getPageIndex(), query.getPageSize(),wmOmNoticeHMapper.getOrderDetailsCount(query));
        page1.setRecords(byPage);
        return PageDTO.create(page1,msMapper::outDetailDOTooutDetailDTO);
    }

    public  ResponseEntity<byte[]> selectExcel(OutDetailQuery query){
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        ResponseEntity<byte[]> responseEntity = null;
        try {
            //首先将数据从数据库查询出来
            List<OutDetailExcelDO> OutDetailExcelDO = wmOmNoticeHMapper.selectAll(query);
            export("出库明细", outputStream, OutDetailExcelDO.class, OutDetailExcelDO);
            HttpHeaders httpHeaders = new HttpHeaders();
            httpHeaders.setContentType(MediaType.parseMediaType(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"));
            // 设置文件名
            ContentDisposition contentDisposition = ContentDisposition.builder("attachment")
                    .filename("出库明细.xlsx", java.nio.charset.StandardCharsets.UTF_8)
                    .build();
            httpHeaders.setContentDisposition(contentDisposition);
            byte[] byteArray = outputStream.toByteArray();
            responseEntity = new ResponseEntity<>(byteArray, httpHeaders, HttpStatus.OK);
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            try {
                //关闭流
                outputStream.close();
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }
        return responseEntity;
    }

    private static final int MAX_COUNT_PER_SHEET = 5000;
    @Resource
    private UserHolder userHolder;
    /**
     * 导出到输出流
     *
     * @param sheetName sheet名称
     * @param os        输出流
     * @param clazz     导出数据类型
     * @param dataList  导出的数据集
     * @param <T>       生成元素实体类类型
     * @throws IOException IO异常
     */
    private <T> void export(String sheetName, OutputStream os, Class<T> clazz, List<T> dataList) throws IOException {
        HorizontalCellStyleStrategy horizontalCellStyleStrategy = new HorizontalCellStyleStrategy(ExcelStyleUtils.getHeadStyle(), ExcelStyleUtils.getContentStyle());
        //通过工具类设置表头样式
        ExcelWriterBuilder builder = EasyExcel.write(os, clazz).registerWriteHandler(
                        new WorkbookWriteHandler() {
                            public void afterWorkbookDispose(WriteWorkbookHolder writeWorkbookHolder) {
                                // 获取当前 Sheet
                                Sheet sheet = writeWorkbookHolder.getWorkbook().getSheetAt(0);
                                // 创建标题行
                                Row titleRow = sheet.createRow(0);
                                Cell titleCell = titleRow.createCell(0);
                                String username = null;
                                try {
                                    UserDTO currentUser = userHolder.getCurrentUser();
                                    username = currentUser.getUsername();
                                } catch (Exception e) {
                                    username = "管理人";
                                }
                                //创建管理人行
                                Row secondRow = sheet.createRow(1);
                                Cell secondCell = secondRow.createCell(0);
                                secondCell.setCellValue("导出人:" + username);
                                //设置第二行的样式
                                CellStyle secondStyle = sheet.getWorkbook().createCellStyle();
                                Font secondFront = sheet.getWorkbook().createFont();
                                secondFront.setFontName("Arial");
                                secondFront.setFontHeightInPoints((short) 10);
                                secondStyle.setFont(secondFront);
                                secondStyle.setAlignment(HorizontalAlignment.RIGHT);
                                secondCell.setCellStyle(secondStyle);
                                // 设置标题内容和样式
                                titleCell.setCellValue("出库明细导出列表");
                                CellStyle titleStyle = sheet.getWorkbook().createCellStyle();
                                Font titleFont = sheet.getWorkbook().createFont();
                                titleFont.setFontName("Arial");
                                titleFont.setBold(true); // 加粗
                                titleFont.setFontHeightInPoints((short) 12); // 字体大小
                                titleStyle.setFont(titleFont);
                                titleStyle.setAlignment(HorizontalAlignment.CENTER); // 居中
                                titleCell.setCellStyle(titleStyle);
                                // 合并单元格（如果需要）
                                sheet.addMergedRegion(new CellRangeAddress(0, 0, 0, 27)); // 合并第 1 行的第 1 列到第 28 列
                                sheet.addMergedRegion(new CellRangeAddress(1, 1, 0, 27));
                            }
                        }
                )
                .registerWriteHandler(horizontalCellStyleStrategy);
        ExcelWriter writer = builder.build();
        //计算总页数
        int sheetCount = dataList.size() / MAX_COUNT_PER_SHEET;
        sheetCount = dataList.size() % MAX_COUNT_PER_SHEET == 0 ? sheetCount : sheetCount + 1;
        //循环构建分页
        for (int i = 0; i < sheetCount; i++) {
            //创建一个页签
            WriteSheet sheet = new WriteSheet();
            sheet.setSheetNo(i);
            sheet.setSheetName(sheetName + (i + 1));
            //设置数据起始位置
            int start = i * MAX_COUNT_PER_SHEET;
            int end = (i + 1) * MAX_COUNT_PER_SHEET;
            end = Math.min(end, dataList.size());
            //从第三行开始写数据
            sheet.setRelativeHeadRowIndex(2);
            //写入数据到页签
            writer.write(dataList.subList(start, end), sheet);
        }
        writer.finish();
        os.close();
    }


    private WmOmNoticeH findNotice(String id) {
        WmOmNoticeH notice = wmOmNoticeHMapper.selectByNoticeId(id);
        if (notice == null) {
            notice = wmOmNoticeHMapper.selectById(id);
        }
        return notice;
    }

    /**
     * 组装通知单明细 + 出库任务的打印行
     */
    private List<java.util.Map<String, Object>> buildPrintItems(String omNoticeId) {
        List<WmOmNoticeI> items = wmOmNoticeIMapper.selectList(new QueryWrapper<WmOmNoticeI>()
                .eq("om_notice_id", omNoticeId));
        List<WmOmQmI> qmList = wmOmQmIMapper.selectList(new QueryWrapper<WmOmQmI>()
                .eq("om_notice_id", omNoticeId));
        List<java.util.Map<String, Object>> rows = new ArrayList<>();
        for (WmOmNoticeI item : items) {
            WmOmQmI qm = null;
            for (WmOmQmI candidate : qmList) {
                if (item.getId() != null && item.getId().equals(candidate.getIomNoticeItem())) {
                    qm = candidate;
                    break;
                }
            }
            if (qm == null) {
                for (WmOmQmI candidate : qmList) {
                    if (item.getGoodsId() != null && item.getGoodsId().equals(candidate.getGoodsId())) {
                        qm = candidate;
                        break;
                    }
                }
            }
            java.util.Map<String, Object> row = new HashMap<>();
            row.put("binOm", item.getBinOm());
            row.put("goodsText", StrUtil.isNotBlank(item.getGoodsText())
                    ? item.getGoodsText() : item.getGoodsName());
            row.put("goodsName", item.getGoodsName());
            row.put("goodsUnit", item.getGoodsUnit());
            row.put("goodsProData", item.getGoodsProData());
            row.put("goodsQua", item.getGoodsQua());
            row.put("goodsQuaok", item.getGoodsQuaok());
            row.put("goodsId", item.getGoodsId());
            row.put("sku", item.getSku());
            row.put("cusName", item.getCusName());
            row.put("url", qm != null && StrUtil.isNotBlank(qm.getBarcode())
                    ? qm.getBarcode() : item.getBarcode());
            row.put("qmOkQuat", qm != null ? qm.getQmOkQuat() : item.getGoodsQua());
            row.put("goodsBatch", qm != null ? qm.getGoodsBatch() : item.getGoodsBatch());
            row.put("shpGuiGe", qm != null ? qm.getShpGuiGe() : null);
            row.put("tinZhl", qm != null ? qm.getTinZhl() : null);
            row.put("tinTj", qm != null ? qm.getTinTj() : null);
            row.put("binId", qm != null ? qm.getBinId() : item.getBinId());
            row.put("baozhiqi", qm != null ? qm.getBaozhiqi() : item.getBzhiQi());
            row.put("itemText", qm != null ? qm.getItemText() : item.getOmBeiZhu());
            rows.add(row);
        }
        return rows;
    }

    private ResponseEntity<byte[]> pdfResponse(ByteArrayOutputStream outputStream, String filename) {
        HttpHeaders httpHeaders = new HttpHeaders();
        httpHeaders.setContentType(MediaType.APPLICATION_PDF);
        ContentDisposition contentDisposition = ContentDisposition.builder("attachment")
                .filename(filename, java.nio.charset.StandardCharsets.UTF_8)
                .build();
        httpHeaders.setContentDisposition(contentDisposition);
        return new ResponseEntity<>(outputStream.toByteArray(), httpHeaders, HttpStatus.OK);
    }

    @Override
    public ResponseEntity<byte[]> queryOutGoodsList(String id) {
        WmOmNoticeH wmOmNoticeH = findNotice(id);
        if (wmOmNoticeH == null) {
            return ResponseEntity.notFound().build();
        }
        List<java.util.Map<String, Object>> items = buildPrintItems(wmOmNoticeH.getOmNoticeId());
        HashMap<String, Object> map = new HashMap<>();
        map.put("cusCode", wmOmNoticeH.getCusCode());
        map.put("omBeizhu", wmOmNoticeH.getOmBeizhu());
        map.put("omNoticeId", wmOmNoticeH.getOmNoticeId());
        map.put("delvAddr", wmOmNoticeH.getDelvAddr());
        map.put("delvMember", wmOmNoticeH.getDelvMember());
        map.put("delvMobile", wmOmNoticeH.getDelvMobile());
        map.put("fhUser", wmOmNoticeH.getFhUser());
        map.put("items", items);
        if (!items.isEmpty()) {
            map.put("url", items.get(0).get("url"));
        }
        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        pdfComponent.generateToStream("goodlist.fo", map, byteArrayOutputStream);
        return pdfResponse(byteArrayOutputStream, "出库单.pdf");
    }

    @Override
    public ResponseEntity<byte[]> queryPickingList(String id) {
        WmOmNoticeH wmOmNoticeH = findNotice(id);
        if (wmOmNoticeH == null) {
            return ResponseEntity.notFound().build();
        }
        List<java.util.Map<String, Object>> items = buildPrintItems(wmOmNoticeH.getOmNoticeId());
        HashMap<String, Object> map = new HashMap<>();
        map.put("omBeizhu", wmOmNoticeH.getOmBeizhu());
        map.put("delvAddr", wmOmNoticeH.getDelvAddr());
        map.put("createDate", wmOmNoticeH.getCreateDate());
        map.put("id", wmOmNoticeH.getOmNoticeId());
        map.put("omNoticeId", wmOmNoticeH.getOmNoticeId());
        map.put("jhUser", wmOmNoticeH.getJhUser());
        map.put("items", items);
        if (!items.isEmpty()) {
            java.util.Map<String, Object> first = items.get(0);
            map.put("binOm", first.get("binOm"));
            map.put("cusName", first.get("cusName"));
            map.put("goodsQua", first.get("goodsQua"));
            map.put("goodsQuaok", first.get("goodsQuaok"));
            map.put("tinTj", first.get("tinTj"));
            map.put("tinZhl", first.get("tinZhl"));
            map.put("url", first.get("url"));
        }
        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        pdfComponent.generateToStream("pickinglists.fo", map, byteArrayOutputStream);
        return pdfResponse(byteArrayOutputStream, "拣货单.pdf");
    }

    @Override
    public PageDTO<OutNoticeListDTO> getNoticeList(OutGoodNoticeQuery query) {
        Page<WmOmNoticeH> page = new Page<>(query.getPageIndex(),query.getPageSize());
        Page<WmOmNoticeH> resultPage = wmOmNoticeHMapper.selectNoticeList(page,query);
        return PageDTO.create(resultPage, msMapper::wmOmNoticeHToOutNoticeListDTO);
    }

    @Override
    public void saveFujian(String omNoticeId, String fuJian) {
        wmOmNoticeHMapper.saveFujian(omNoticeId,fuJian);
    }


    public String updateById(WonhDTO modify) {
        if(wmOmNoticeHMapper.updateWmOmNoticeH(modify)){
            return "修改成功";
        }
        return "修改失败";
    }

    @Override
    public WmOmNoticeH queryByOmId(WonQuery query) {
        QueryWrapper<WmOmNoticeH> wmOmNoticeHQueryWrapper = new QueryWrapper<>();
        wmOmNoticeHQueryWrapper.like("om_notice_id",query.getOmNoticeId());
        return baseMapper.selectOne(wmOmNoticeHQueryWrapper);
    }





}
