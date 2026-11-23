<script lang="ts" setup>
definePage({
	meta: {
		menuType: "page",
		text: "计费日期",
		icon: "IconSetting",
	},
});
</script>

<template>
	<section class="plan-out">
		<el-alert type="warning" :closable="false" show-icon title="该页面不在《版本计划》计费配置分支内">
			<template #default>
				<p>
					《版本计划.emmx》的「计费配置（64）」分支共 11 个子模块（客户计费方式、客户计费属性、费用名称、费用类型、计费商品分类、计量类型、计费方式、费用模板、仓储费率、价格类型、计费合同引用节点），<b>不包含「计费日期」</b>。
				</p>
				<p>
					对应数据表 <code>wm_day_cost_conf</code>（字段 <code>cost_date</code>、<code>cost_sf</code>）在全项目 C++ / Java / 前端代码中<b>无任何引用</b>，属未启用的历史表。
				</p>
				<p>
					处置建议：由业务确认后<b>移除该菜单</b>，或明确其与「仓储费率 / 费用模板」的关系后单独立项。当前保留页面占位，避免菜单与路由缺失。
				</p>
			</template>
		</el-alert>
	</section>
</template>

<style lang="scss" scoped>
.plan-out {
	padding: 16px;

	p {
		margin: 6px 0;
		line-height: 1.7;
	}
}
</style>
