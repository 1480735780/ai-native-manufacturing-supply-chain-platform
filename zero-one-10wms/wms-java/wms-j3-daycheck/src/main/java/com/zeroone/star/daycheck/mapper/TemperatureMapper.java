package com.zeroone.star.daycheck.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.daycheck.entity.Temperature;
import com.zeroone.star.project.dto.j3.daycheck.tem.TemperatureDTO;
import com.zeroone.star.project.vo.j3.daycheck.tem.TemperatureVO;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface TemperatureMapper extends BaseMapper<Temperature> {

    void saveTemp(Temperature temperature);

    void deleteTemps(List<String> ids);

    void updateTemp(Temperature temperature);

    @Select("select * from zo_wms.wm_wendu where id = #{id}")
    Temperature TemperatureById(String id);

    /** 巡检分页：显式列（含 create_date）+ wendu_cjsj/id 稳定排序，Page 由插件注入分页。 */
    Page<TemperatureVO> pageQueryAll(Page<TemperatureVO> page);

    @Select("SELECT * FROM zo_wms.wm_wendu")
    List<Temperature> selectAllFromAnnotation();

    void saveBatch(@Param("list") List<Temperature> list);

}
