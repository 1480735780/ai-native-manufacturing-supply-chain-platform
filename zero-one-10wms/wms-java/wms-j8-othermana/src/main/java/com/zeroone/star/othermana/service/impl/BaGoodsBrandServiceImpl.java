package com.zeroone.star.othermana.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.othermana.mapper.BaGoodsBrandMapper;
import com.zeroone.star.othermana.service.BaGoodsBrandService;
import com.zeroone.star.project.components.fastdfs.FastDfsClientComponent;
import com.zeroone.star.project.components.fastdfs.FastDfsFileInfo;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j8.other.goodsbrand.GoodsBrandDTO;
import com.zeroone.star.project.query.j8.other.goodsbrand.GoodsBrandQuery;
import com.zeroone.star.project.vo.j8.other.goodsbrand.GoodsBrandAddReqVO;
import com.zeroone.star.project.vo.j8.other.goodsbrand.GoodsBrandNameVO;
import com.zeroone.star.project.vo.j8.other.goodsbrand.GoodsBrandUpdateOprationRespVO;
import com.zeroone.star.project.vo.j8.other.goodsbrand.GoodsBrandUpdateReqVO;
import com.zeroone.star.project.vo.j8.other.goodsbrand.GoodsBrandVO;
import org.springframework.beans.BeanUtils;
import lombok.SneakyThrows;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.util.List;
import java.util.UUID;

/**
 * @author 陈尚益
 * @description 针对表【ba_goods_brand(品牌信息)】的数据库操作Service实现
 * @createDate 2025-03-08 11:38:45
 */
@Service
public class BaGoodsBrandServiceImpl extends ServiceImpl<BaGoodsBrandMapper, GoodsBrandVO>
        implements BaGoodsBrandService {

    @Resource
    private BaGoodsBrandMapper baGoodsBrandMapper;

    @Resource
    private FastDfsClientComponent dfs;

    @Value("${fastdfs.nginx-servers}")
    private String urlPrefix;

    @Override
    public List<GoodsBrandNameVO> queryGoodsBrandNameList() {
        QueryWrapper<GoodsBrandVO> wrapper = new QueryWrapper<>();
        wrapper.select("id", "goods_brand_code", "goods_brand_name");
        wrapper.eq("goods_brand_del", "0").or().isNull("goods_brand_del");
        wrapper.orderByAsc("goods_brand_code");
        List<GoodsBrandVO> brands = baseMapper.selectList(wrapper);
        List<GoodsBrandNameVO> result = new java.util.ArrayList<>(brands.size());
        for (GoodsBrandVO brand : brands) {
            GoodsBrandNameVO vo = new GoodsBrandNameVO();
            BeanUtils.copyProperties(brand, vo);
            result.add(vo);
        }
        return result;
    }

    @Override
    public PageDTO<GoodsBrandVO> queryGoodsBrandPage(GoodsBrandQuery query) {
        Page<GoodsBrandVO> page = new Page<>(query.getPageIndex(), query.getPageSize());
        Page<GoodsBrandVO> result = baseMapper.selectPage(page, buildQueryWrapper(query));
        return PageDTO.create(result, GoodsBrandVO.class);
    }

    @Override
    public List<GoodsBrandVO> queryGoodsBrandAll(GoodsBrandQuery query) {
        return baseMapper.selectList(buildQueryWrapper(query));
    }

    /** 列表查询与导出共用的条件构造 */
    private QueryWrapper<GoodsBrandVO> buildQueryWrapper(GoodsBrandQuery query) {
        QueryWrapper<GoodsBrandVO> wrapper = new QueryWrapper<>();
        if (query.getGoodsBrandName() != null && !query.getGoodsBrandName().equals("")) {
            wrapper.like("goods_brand_name", query.getGoodsBrandName());
        }
        if (query.getGoodsBrandCode() != null && !query.getGoodsBrandCode().equals("")) {
            wrapper.like("goods_brand_code", query.getGoodsBrandCode());
        }
        if (query.getOrder() != null && !query.getOrder().equals("") && query.getSort() != null && !query.getSort().equals("")) {
            wrapper.orderBy(true, query.getOrder().equals("asc"), query.getSort());
        }
        return wrapper;
    }

    @SneakyThrows
    @Override
    public boolean addGoodsBrand(GoodsBrandAddReqVO goodsBrandAddReqVO) {
        GoodsBrandDTO goodsBrandDTO = new GoodsBrandDTO();
        // 处理图片上传
        MultipartFile goodsBrandPic = goodsBrandAddReqVO.getGoodsBrandPic();
        String originalFilename = goodsBrandPic.getOriginalFilename();
        String suffix = originalFilename.substring(originalFilename.lastIndexOf(".")+1);
        FastDfsFileInfo info = dfs.uploadFile(goodsBrandPic.getBytes(), suffix);
        if (info != null) {
            String s = dfs.fetchUrl(info, urlPrefix, true);
            goodsBrandDTO.setGoodsBrandPic(s);
        }
        goodsBrandDTO.setGoodsBrandCode(goodsBrandAddReqVO.getGoodsBrandCode());
        goodsBrandDTO.setGoodsBrandName(goodsBrandAddReqVO.getGoodsBrandName());
        goodsBrandDTO.setGoodsBrandWww(goodsBrandAddReqVO.getGoodsBrandWww());
        goodsBrandDTO.setGoodsBrandText(goodsBrandAddReqVO.getGoodsBrandText());
        goodsBrandDTO.setGoodsBrandDel(goodsBrandAddReqVO.getGoodsBrandDel());
        goodsBrandDTO.setId(UUID.randomUUID().toString());
        return baGoodsBrandMapper.addGoodsBrand(goodsBrandDTO);
    }

    @Override
    public GoodsBrandUpdateOprationRespVO oprationGetById(String id) {
        GoodsBrandVO goodsBrandVO = baseMapper.selectById(id);
        GoodsBrandUpdateOprationRespVO goodsBrandUpdateOprationRespVO = new GoodsBrandUpdateOprationRespVO();
        goodsBrandUpdateOprationRespVO.setId(goodsBrandVO.getId());
        goodsBrandUpdateOprationRespVO.setGoodsBrandCode(goodsBrandVO.getGoodsBrandCode());
        goodsBrandUpdateOprationRespVO.setGoodsBrandName(goodsBrandVO.getGoodsBrandName());
        goodsBrandUpdateOprationRespVO.setGoodsBrandWww(goodsBrandVO.getGoodsBrandWww());
        goodsBrandUpdateOprationRespVO.setGoodsBrandPic(goodsBrandVO.getGoodsBrandPic());
        goodsBrandUpdateOprationRespVO.setGoodsBrandText(goodsBrandVO.getGoodsBrandText());
        goodsBrandUpdateOprationRespVO.setGoodsBrandDel(goodsBrandVO.getGoodsBrandDel());
        return goodsBrandUpdateOprationRespVO;
    }

    @SneakyThrows
    @Override
    public boolean updateGoodsBrand(GoodsBrandUpdateReqVO vo) {
        if (vo == null || vo.getId() == null || vo.getId().trim().isEmpty()) {
            return false;
        }
        GoodsBrandDTO dto = new GoodsBrandDTO();
        BeanUtils.copyProperties(vo, dto, "goodsBrandPic");
        dto.setId(vo.getId());
        // 上传了新图片才替换，否则保留数据库中已有的图片
        MultipartFile pic = vo.getGoodsBrandPic();
        if (pic != null && !pic.isEmpty() && pic.getOriginalFilename() != null) {
            String originalFilename = pic.getOriginalFilename();
            String suffix = originalFilename.substring(originalFilename.lastIndexOf(".") + 1);
            FastDfsFileInfo info = dfs.uploadFile(pic.getBytes(), suffix);
            if (info != null) {
                dto.setGoodsBrandPic(dfs.fetchUrl(info, urlPrefix, true));
            }
        }
        return baGoodsBrandMapper.updateGoodsBrand(dto) > 0;
    }

    @Override
    public boolean saveAll(List<GoodsBrandVO> list) {
        for (GoodsBrandVO goodsBrandVO : list) {
            baseMapper.insert(goodsBrandVO);
        }
        return true;
    }
}




