import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// Global styles
import './styles/variables.css'

// Directives
import { vTooltip } from './directives/tooltip'

// Components
import GlobalSearch from './components/GlobalSearch.vue'
import GlobalLoader from './components/GlobalLoader.vue'
import Skeleton from './components/Skeleton.vue'

// Utils
import { shortcutManager } from './utils/shortcuts'

const app = createApp(App)

// Plugins
app.use(createPinia())
app.use(router)

// Global components
app.component('GlobalSearch', GlobalSearch)
app.component('GlobalLoader', GlobalLoader)
app.component('Skeleton', Skeleton)

// Global directives
app.directive('tooltip', vTooltip)

// Initialize shortcut manager
shortcutManager.bind()

app.mount('#app')
