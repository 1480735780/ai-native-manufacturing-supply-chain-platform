import { createApp } from "vue";
import { createPinia } from "pinia";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import FcDesigner from "@form-create/designer";
import ElementPlus from "element-plus";
import zhCn from "element-plus/dist/locale/zh-cn.mjs";

import App from "./App.vue";
import router from "./routers";
import i18n from "./views/i18n";
import installHttp from "./plugins/http";
import installElIcon from "./plugins/el-icon";
import "element-plus/es/components/message/style/css";
import "./assets/main.css";
import "./assets/iconfont/iconfont.css";

const app = createApp(App);
app.use(createPinia().use(piniaPluginPersistedstate));
app.use(ElementPlus, { locale: zhCn });
app.use(FcDesigner);
app.use(i18n);
installElIcon(app);

// 路由守卫会发起身份请求，必须先安装 HTTP 拦截器再注册路由。
installHttp(router);
installAxiosWithVueUse(router, axiosInstance);
app.use(router);
app.mount("#app");
