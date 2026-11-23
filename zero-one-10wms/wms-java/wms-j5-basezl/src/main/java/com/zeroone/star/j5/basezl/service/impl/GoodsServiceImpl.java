package com.zeroone.star.j5.basezl.service.impl;

import cn.hutool.core.date.DateTime;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.j5.basezl.entity.customer.CustomerDO;
import com.zeroone.star.j5.basezl.entity.customer.CustomerExcel;
import com.zeroone.star.j5.basezl.entity.good.GoodsExcel;
import com.zeroone.star.j5.basezl.entity.good.MdGoods;
import com.zeroone.star.j5.basezl.mapper.MdGoodsMapper;
import com.zeroone.star.j5.basezl.service.GoodsService;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.components.pdf.PdfComponent;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j5.basezl.goods.GoodsAddDTO;
import com.zeroone.star.project.dto.j5.basezl.goods.GoodsDetailDTO;
import com.zeroone.star.project.dto.j5.basezl.goods.GoodsListDTO;
import com.zeroone.star.project.dto.j5.basezl.goods.GoodsModifyDTO;
import com.zeroone.star.project.query.j5.basezl.goods.GoodsQuery;
import com.zeroone.star.project.vo.JsonVO;
import lombok.extern.slf4j.Slf4j;
import org.mapstruct.Mapper;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.io.ByteArrayOutputStream;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Mapper(componentModel = "spring")
interface MSGoodsMapper{

    MdGoods GoodsAddDtO2MdGoods(GoodsAddDTO goodsAddDTO);

    GoodsDetailDTO mdGoods2GoodsDetailDTO(MdGoods mdGoods);

    GoodsListDTO mdGoods2GoodsListDTO(MdGoods mdGoods);

    MdGoods goodsModifyDTO2MdGoods(GoodsModifyDTO goodsModifyDTO);

    GoodsExcel goodsDetailDto2GoodsExcel(GoodsDetailDTO goodsDetailDTO);

    MdGoods goodsExcel2MdGoods(GoodsExcel goodsExcel);
}

/**
 * <p>
 * 商品信息 服务实现类
 * </p>
 *
 * @author heavydrink
 * @since 2025-02-27
 */
@Service
@Slf4j
public class GoodsServiceImpl extends ServiceImpl<MdGoodsMapper, MdGoods> implements GoodsService {

    @Resource
    MSGoodsMapper msMapper;

    @Resource
    EasyExcelComponent excel;

    @Resource
    PdfComponent pdf;

    @Resource
    UserHolder userHolder;

    @Override
    public PageDTO<GoodsListDTO> queryAll(GoodsQuery query) {
        Page<MdGoods> page = new Page<>(query.getPageIndex(), query.getPageSize());
        QueryWrapper<MdGoods> queryWrapper = new QueryWrapper<>();
        if(query.getSysCompanyCode()!=null) queryWrapper.eq("sys_company_code",query.getSysCompanyCode());
        if(query.getShpMingCheng()!=null) queryWrapper.like("shp_ming_cheng",query.getShpMingCheng());
        if(query.getYwMingCheng()!=null) queryWrapper.like("yw_ming_cheng",query.getYwMingCheng());
        if(query.getRwMingCheng()!=null) queryWrapper.like("rw_ming_cheng",query.getRwMingCheng());
        if(query.getShpBianMa()!=null) queryWrapper.like("shp_bian_ma",query.getShpBianMa());
        if(query.getShpBianMakh()!=null) queryWrapper.like("SHP_BIAN_MAKH",query.getShpBianMakh());
        if(query.getShpTiaoMa()!=null) queryWrapper.like("shp_tiao_ma",query.getShpTiaoMa());
        if(query.getZhuangTai()!=null) queryWrapper.eq("zhuang_tai",query.getZhuangTai());

        Page<MdGoods> ps = baseMapper.selectPage(page, queryWrapper);
        return PageDTO.create(ps, msMapper::mdGoods2GoodsListDTO);
    }

    @Override
    public GoodsDetailDTO queryOne(String shp_bian_ma) {
        if (shp_bian_ma == null || shp_bian_ma.trim().isEmpty()) {
            return null;
        }
        QueryWrapper<MdGoods> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("shp_bian_ma", shp_bian_ma);
        MdGoods mdGoods = baseMapper.selectOne(queryWrapper);
        if (mdGoods == null) {
            return null;
        }
        return msMapper.mdGoods2GoodsDetailDTO(mdGoods);
    }

    @Override
    public String addGoods(GoodsAddDTO goodsAddDTO) {
        MdGoods mdGoods = msMapper.GoodsAddDtO2MdGoods(goodsAddDTO);
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        try{
            UserDTO user = userHolder.getCurrentUser();
            mdGoods.setCreateBy(user.getUsername());
            mdGoods.setCreateName(user.getRealname());
            mdGoods.setSysOrgCode(user.getOrgCode());
            mdGoods.setCreateDate(LocalDateTime.parse(LocalDateTime.now().format(formatter),formatter));

        }catch (Exception e){
            log.info("没有得到用户信息");
        }
        Integer ans = baseMapper.insert(mdGoods);
        return ans.toString();
    }

    @Override
    public String updateGoods(GoodsModifyDTO goodsModifyDTO) {
        MdGoods mdGoods = msMapper.goodsModifyDTO2MdGoods(goodsModifyDTO);
        LambdaUpdateWrapper<MdGoods> lambdaUpdateWrapper = new LambdaUpdateWrapper<>();
        lambdaUpdateWrapper.eq(MdGoods::getShpBianMa, mdGoods.getShpBianMa());
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        try{
            UserDTO user = userHolder.getCurrentUser();
            mdGoods.setUpdateBy(user.getUsername());
            mdGoods.setUpdateName(user.getRealname());
            mdGoods.setUpdateDate(LocalDateTime.parse(LocalDateTime.now().format(formatter),formatter));
        }catch(Exception e){
            log.info("没有得到用户信息");
        }



        Integer ans = baseMapper.update(mdGoods, lambdaUpdateWrapper);
        return ans.toString();
    }

    @Override
    public String deleteGoods(List<String> shpBianMas) {
        if (shpBianMas == null || shpBianMas.isEmpty()) {
            return "0";
        }
        LambdaQueryWrapper<MdGoods> wrapper = new LambdaQueryWrapper<>();
        wrapper.in(MdGoods::getShpBianMa, shpBianMas);
        return String.valueOf(baseMapper.delete(wrapper));
    }

    @Override
    public JsonVO<String> uploadGoods(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            return JsonVO.fail("导入文件不能为空");
        }
        List<GoodsExcel> goodsExcelList = excel.parseExcel(file, GoodsExcel.class);
        int skip = 0;
        int fail = 0;
        List<MdGoods> goodsList = new ArrayList<>();
        for (GoodsExcel goodsExcel : goodsExcelList) {
            if (goodsExcel == null || goodsExcel.getShpBianMa() == null || goodsExcel.getShpBianMa().trim().isEmpty()) {
                fail++;
                continue;
            }
            QueryWrapper<MdGoods> wrapper = new QueryWrapper<>();
            wrapper.eq("shp_bian_ma", goodsExcel.getShpBianMa());
            if (baseMapper.selectCount(wrapper) > 0) {
                skip++;
                continue;
            }
            goodsList.add(msMapper.goodsExcel2MdGoods(goodsExcel));
        }
        if (goodsList.isEmpty()) {
            return JsonVO.success(String.format("导入成功 0 条，跳过重复 %d 条，失败 %d 条", skip, fail));
        }
        boolean b = this.saveBatch(goodsList);
        if (!b) {
            return JsonVO.fail("导入失败");
        }
        return JsonVO.success(String.format("导入成功 %d 条，跳过重复 %d 条，失败 %d 条", goodsList.size(), skip, fail));
    }

    @Override
    public ResponseEntity<byte[]> exportGoods(List<String> shpBianMas, GoodsQuery query) {
        try( ByteArrayOutputStream out = new ByteArrayOutputStream();){
            List<GoodsExcel> data = new ArrayList<>();
            if (shpBianMas != null && !shpBianMas.isEmpty()) {
                // 勾选优先：按商品编码导出
                for (String shpbianma : shpBianMas) {
                    GoodsDetailDTO goodsDetailDTO = queryOne(shpbianma);
                    if (goodsDetailDTO != null) {
                        data.add(msMapper.goodsDetailDto2GoodsExcel(goodsDetailDTO));
                    }
                }
            } else {
                // 未勾选：按当前查询条件导出全部
                QueryWrapper<MdGoods> queryWrapper = new QueryWrapper<>();
                if (query != null) {
                    if (query.getSysCompanyCode() != null) queryWrapper.eq("sys_company_code", query.getSysCompanyCode());
                    if (query.getShpMingCheng() != null) queryWrapper.like("shp_ming_cheng", query.getShpMingCheng());
                    if (query.getYwMingCheng() != null) queryWrapper.like("yw_ming_cheng", query.getYwMingCheng());
                    if (query.getRwMingCheng() != null) queryWrapper.like("rw_ming_cheng", query.getRwMingCheng());
                    if (query.getShpBianMa() != null) queryWrapper.like("shp_bian_ma", query.getShpBianMa());
                    if (query.getShpBianMakh() != null) queryWrapper.like("SHP_BIAN_MAKH", query.getShpBianMakh());
                    if (query.getShpTiaoMa() != null) queryWrapper.like("shp_tiao_ma", query.getShpTiaoMa());
                    if (query.getZhuangTai() != null) queryWrapper.eq("zhuang_tai", query.getZhuangTai());
                }
                for (MdGoods goods : baseMapper.selectList(queryWrapper)) {
                    data.add(msMapper.goodsDetailDto2GoodsExcel(msMapper.mdGoods2GoodsDetailDTO(goods)));
                }
            }
            excel.export("导出信息",out, GoodsExcel.class,data);
            String filename = "goods_" + DateTime.now().toString("yyyyMMddHHmmssS") + ".xlsx";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentDispositionFormData("attachment", filename);
            headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);

            return new ResponseEntity<>(out.toByteArray(), headers, HttpStatus.CREATED);
        }catch (Exception e){
            log.error("导出商品文件失败", e);
            return new ResponseEntity<>(null, HttpStatus.INTERNAL_SERVER_ERROR);
        }

    }

    @Override
    public ResponseEntity<byte[]> printGoodsTiaoMa(String shpBianMa) {

        try(ByteArrayOutputStream out = new ByteArrayOutputStream();){
            // 定义日期格式化模式
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy/MM/dd");
            GoodsDetailDTO goodsDetailDTO = queryOne(shpBianMa);
            if (goodsDetailDTO == null) {
                return new ResponseEntity<>(null, HttpStatus.NOT_FOUND);
            }

            Map<String,Object> data = new HashMap<>();
            data.put("barcode",shpBianMa);
            data.put("DateTime",LocalDate.now().format(formatter));
            data.put("shpMingCheng",goodsDetailDTO.getShpMingCheng()!=null ? goodsDetailDTO.getShpMingCheng() : " ");
            data.put("shpGuiGe",goodsDetailDTO.getShpGuiGe()!=null ? goodsDetailDTO.getShpGuiGe() : " ");
            data.put("shlDanWei",goodsDetailDTO.getShlDanWei()!=null ? goodsDetailDTO.getShlDanWei() : " ");

            pdf.generateToStream("barcode.fo",data,out);
            byte[] bytes = out.toByteArray();

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_PDF);
            headers.setContentDispositionFormData("attachment","barcode.pdf");
            return new ResponseEntity<>(bytes,headers, HttpStatus.OK);
        }catch (Exception e){
            e.printStackTrace();
            return new ResponseEntity<>(null, HttpStatus.INTERNAL_SERVER_ERROR);
        }

    }

}
