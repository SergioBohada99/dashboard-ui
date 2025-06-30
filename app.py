import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title='Sales Intelligence Dashboard',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='expanded'
)

# -------------- CUSTOM CSS -----------------------
st.markdown(
    '''
    <style>
    html, body, [class*='st-'], .block-container{font-family: 'Inter', sans-serif;}
    .metric-card{padding:1rem;border-radius:1rem;box-shadow:0 3px 6px rgba(52,120,255,.15);text-align:center;margin-bottom:1rem;}
    .metric-card h3{font-size:.9rem;margin-bottom:.25rem;font-weight:500;}
    .metric-card h2{font-size:1.6rem;margin:0;font-weight:600;}
    </style>
    ''',
    unsafe_allow_html=True)

# -------------- DATA LOADING --------------------
@st.cache_data
def load_data(path: str = 'data_aug.csv') -> pd.DataFrame:
    df = pd.read_csv(path, sep='\t', encoding='latin1')
    df['fecha_venta_dt'] = pd.to_datetime(df['fecha_venta'], dayfirst=True, errors='coerce')
    df['revenue'] = df['precio'] * df['unidades_vendidas']
    df['month'] = df['fecha_venta_dt'].dt.to_period('M').astype(str)
    df['week']  = df['fecha_venta_dt'].dt.to_period('W-MON').apply(lambda r: r.start_time.strftime('%Y-%m-%d'))
    df['day']   = df['fecha_venta_dt'].dt.strftime('%Y-%m-%d')
    
    # Calcular margen de ganancia (simulado)
    df['costo_estimado'] = df['precio'] * 0.65  # 65% del precio como costo estimado
    df['margen_ganancia'] = df['precio'] - df['costo_estimado']
    df['margen_porcentual'] = (df['margen_ganancia'] / df['precio']) * 100
    
    return df.dropna(subset=['fecha_venta_dt'])

df = load_data()

# ---------------- SIDEBAR FILTERS ---------------
st.sidebar.header('🔎 Filters')
min_date, max_date = df['fecha_venta_dt'].min(), df['fecha_venta_dt'].max()
start_d, end_d = st.sidebar.date_input('Select date range', (min_date, max_date), min_value=min_date, max_value=max_date)

category_options = ['All'] + sorted(df['categoria'].dropna().unique())
selected_cat = st.sidebar.selectbox('Category', category_options)

# Apply filters
mask = df['fecha_venta_dt'].between(pd.to_datetime(start_d), pd.to_datetime(end_d))
if selected_cat != 'All':
    mask &= df['categoria'] == selected_cat
filtered = df[mask]

# ---------- METRICS ROW -------------------------
col1, col2, col3, col4 = st.columns(4)
metrics = {
    'Total revenue': filtered['revenue'].sum(),
    'Units sold': int(filtered['unidades_vendidas'].sum()),
    'Avg ticket': filtered['precio'].mean(),
    'Unique products': filtered['producto'].nunique()
}
for col,(k,v) in zip([col1,col2,col3,col4],metrics.items()):
    with col:
        st.markdown(f"""
        <div class='metric-card'>
            <h3>{k}</h3>
            <h2>{v:,.0f}</h2>
        </div>
        """,unsafe_allow_html=True)

st.divider()

# ---------- LISTA DE PRODUCTOS ------------------
st.subheader('📦 Lista de productos')
st.markdown("""
**Descripción:** Con este gráfico, realizado a partir del dataset obtenido después del Webscraping, 
se busca corroborar cuales son los productos mas vendidos actualmente en el mercado.
""")

# Obtener los productos más vendidos por unidades
top_products_by_units = (filtered.groupby('producto', as_index=False)
                        .agg({
                            'unidades_vendidas': 'sum',
                            'revenue': 'sum',
                            'precio': 'mean',
                            'categoria': 'first'
                        })
                        .sort_values('unidades_vendidas', ascending=False)
                        .head(15))

# Crear el gráfico de barras horizontal
fig_products = px.bar(
    top_products_by_units,
    x='unidades_vendidas',
    y='producto',
    orientation='h',
    color='categoria',
    title='Top 15 Productos Más Vendidos por Unidades',
    labels={'unidades_vendidas': 'Unidades Vendidas', 'producto': 'Producto'},
    hover_data=['revenue', 'precio']
)

fig_products.update_layout(
    height=600,
    margin=dict(l=0, r=0, t=40, b=0),
    xaxis_title='Unidades Vendidas',
    yaxis_title='Producto',
    showlegend=True
)

# Mejorar la presentación del gráfico
fig_products.update_traces(
    texttemplate='%{x:,}',
    textposition='outside'
)

st.plotly_chart(fig_products, use_container_width=True)

# Mostrar tabla detallada
st.subheader('📊 Detalle de Productos Más Vendidos')
st.dataframe(
    top_products_by_units[['producto', 'unidades_vendidas', 'revenue', 'precio', 'categoria']]
    .rename(columns={
        'producto': 'Producto',
        'unidades_vendidas': 'Unidades Vendidas',
        'revenue': 'Revenue Total',
        'precio': 'Precio Promedio',
        'categoria': 'Categoría'
    })
    .style.format({
        'Unidades Vendidas': '{:,.0f}',
        'Revenue Total': '${:,.0f}',
        'Precio Promedio': '${:,.0f}'
    }),
    use_container_width=True
)

st.divider()

# ---------- PRODUCTOS CON MAYOR MARGEN Y ROTACIÓN ------------------
st.subheader('💰 Productos con mayor margen de ganancia y tasa de rotación')
st.markdown("""
**Descripción:** Este análisis identifica los productos que combinan altos márgenes de ganancia con una 
excelente tasa de rotación de inventario. Los productos en el cuadrante superior derecho representan las 
mejores oportunidades comerciales, ya que generan mayor rentabilidad por unidad vendida y se venden 
frecuentemente, optimizando el retorno de inversión del inventario.
""")

# Calcular métricas por producto
product_metrics = (filtered.groupby('producto', as_index=False)
                  .agg({
                      'unidades_vendidas': 'sum',
                      'margen_porcentual': 'mean',
                      'revenue': 'sum',
                      'precio': 'mean',
                      'categoria': 'first'
                  })
                  .rename(columns={'unidades_vendidas': 'tasa_rotacion'}))

# Filtrar productos con al menos 5 unidades vendidas para evitar outliers
product_metrics = product_metrics[product_metrics['tasa_rotacion'] >= 5]

# Crear gráfico de dispersión
fig_margin_rotation = px.scatter(
    product_metrics,
    x='margen_porcentual',
    y='tasa_rotacion',
    size='revenue',
    color='categoria',
    hover_name='producto',
    title='Margen de Ganancia vs Tasa de Rotación',
    labels={
        'margen_porcentual': 'Margen de Ganancia (%)',
        'tasa_rotacion': 'Tasa de Rotación (Unidades Vendidas)',
        'revenue': 'Revenue Total'
    },
    hover_data=['precio', 'revenue']
)

# Mejorar el diseño del gráfico
fig_margin_rotation.update_layout(
    height=600,
    margin=dict(l=0, r=0, t=40, b=0),
    xaxis_title='Margen de Ganancia (%)',
    yaxis_title='Tasa de Rotación (Unidades Vendidas)',
    showlegend=True
)

# Agregar líneas de referencia para los cuadrantes
fig_margin_rotation.add_hline(
    y=product_metrics['tasa_rotacion'].median(),
    line_dash="dash",
    line_color="gray",
    annotation_text="Mediana Rotación"
)

fig_margin_rotation.add_vline(
    x=product_metrics['margen_porcentual'].median(),
    line_dash="dash", 
    line_color="gray",
    annotation_text="Mediana Margen"
)

st.plotly_chart(fig_margin_rotation, use_container_width=True)

# Mostrar top productos por margen y rotación
col_margin, col_rotation = st.columns(2)

with col_margin:
    st.subheader('🏆 Top 10 por Margen de Ganancia')
    top_margin = product_metrics.nlargest(10, 'margen_porcentual')[['producto', 'margen_porcentual', 'tasa_rotacion', 'revenue', 'categoria']]
    st.dataframe(
        top_margin.rename(columns={
            'producto': 'Producto',
            'margen_porcentual': 'Margen (%)',
            'tasa_rotacion': 'Rotación',
            'revenue': 'Revenue',
            'categoria': 'Categoría'
        }).style.format({
            'Margen (%)': '{:.1f}%',
            'Rotación': '{:,.0f}',
            'Revenue': '${:,.0f}'
        }),
        use_container_width=True
    )

with col_rotation:
    st.subheader('⚡ Top 10 por Tasa de Rotación')
    top_rotation = product_metrics.nlargest(10, 'tasa_rotacion')[['producto', 'tasa_rotacion', 'margen_porcentual', 'revenue', 'categoria']]
    st.dataframe(
        top_rotation.rename(columns={
            'producto': 'Producto',
            'tasa_rotacion': 'Rotación',
            'margen_porcentual': 'Margen (%)',
            'revenue': 'Revenue',
            'categoria': 'Categoría'
        }).style.format({
            'Rotación': '{:,.0f}',
            'Margen (%)': '{:.1f}%',
            'Revenue': '${:,.0f}'
        }),
        use_container_width=True
    )

st.divider()

# ---------- SATISFACCIÓN DEL CLIENTE ------------------
st.subheader('😊 Satisfacción del cliente según el tipo de producto')
st.markdown("""
**Descripción:** Este análisis evalúa la satisfacción del cliente a través de puntajes de 1 a 5 estrellas, 
permitiendo identificar qué categorías de productos generan mayor satisfacción entre los consumidores. 
Esta información es crucial para optimizar el portafolio de productos y mejorar la experiencia del cliente, 
identificando oportunidades de mejora y productos que superan las expectativas del mercado.
""")

# Calcular satisfacción promedio por categoría
satisfaction_by_category = (filtered.groupby('categoria', as_index=False)
                          .agg({
                              'satisfaccion_cliente': ['mean', 'count'],
                              'revenue': 'sum'
                          })
                          .round(2))

# Flatten column names
satisfaction_by_category.columns = ['categoria', 'satisfaccion_promedio', 'total_ventas', 'revenue_total']
satisfaction_by_category = satisfaction_by_category.sort_values('satisfaccion_promedio', ascending=False)

# Crear gráfico de barras para satisfacción por categoría
fig_satisfaction = px.bar(
    satisfaction_by_category,
    x='categoria',
    y='satisfaccion_promedio',
    color='satisfaccion_promedio',
    title='Satisfacción Promedio por Categoría de Producto',
    labels={'satisfaccion_promedio': 'Satisfacción Promedio (1-5)', 'categoria': 'Categoría'},
    color_continuous_scale='RdYlGn'
)

fig_satisfaction.update_layout(
    height=500,
    margin=dict(l=0, r=0, t=40, b=0),
    xaxis_title='Categoría',
    yaxis_title='Satisfacción Promedio',
    showlegend=False
)

# Agregar valores en las barras
fig_satisfaction.update_traces(
    texttemplate='%{y:.2f}',
    textposition='outside'
)

st.plotly_chart(fig_satisfaction, use_container_width=True)

# Mostrar distribución de satisfacción
col_sat1, col_sat2 = st.columns(2)

with col_sat1:
    st.subheader('📊 Distribución de Satisfacción')
    satisfaction_dist = filtered['satisfaccion_cliente'].value_counts().sort_index()
    
    fig_dist = px.pie(
        values=satisfaction_dist.values,
        names=[f'{i} Estrellas' for i in satisfaction_dist.index],
        title='Distribución de Puntajes de Satisfacción'
    )
    fig_dist.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_dist, use_container_width=True)

with col_sat2:
    st.subheader('🏆 Top Categorías por Satisfacción')
    st.dataframe(
        satisfaction_by_category[['categoria', 'satisfaccion_promedio', 'total_ventas', 'revenue_total']]
        .rename(columns={
            'categoria': 'Categoría',
            'satisfaccion_promedio': 'Satisfacción',
            'total_ventas': 'Total Ventas',
            'revenue_total': 'Revenue Total'
        })
        .style.format({
            'Satisfacción': '{:.2f}',
            'Total Ventas': '{:,.0f}',
            'Revenue Total': '${:,.0f}'
        }),
        use_container_width=True
    )

st.divider()

# ---------- DIFERENCIA DE PRECIOS ENTRE CANALES ------------------
st.subheader('🛒 Diferencia de precio entre canales: HomeCenter vs Amazon vs MercadoLibre')
st.markdown("""
**Descripción:** Este análisis compara los precios de los mismos productos entre diferentes canales de venta, 
permitiendo identificar oportunidades de arbitraje y entender la estrategia de precios de cada plataforma. 
La información ayuda a optimizar la estrategia de distribución y pricing, identificando qué canal ofrece 
mejores precios para diferentes categorías de productos y cómo esto afecta la competitividad del mercado.
""")

# Calcular diferencias de precios por categoría
price_comparison = (filtered.groupby('categoria', as_index=False)
                   .agg({
                       'precio_homecenter': 'mean',
                       'precio_amazon': 'mean',
                       'precio_mercadolibre': 'mean',
                       'revenue': 'sum'
                   })
                   .round(0))

# Calcular diferencias porcentuales
price_comparison['diff_amazon_hc'] = ((price_comparison['precio_amazon'] - price_comparison['precio_homecenter']) / price_comparison['precio_homecenter'] * 100).round(1)
price_comparison['diff_ml_hc'] = ((price_comparison['precio_mercadolibre'] - price_comparison['precio_homecenter']) / price_comparison['precio_homecenter'] * 100).round(1)

# Crear gráfico de comparación de precios
fig_price_comparison = px.bar(
    price_comparison,
    x='categoria',
    y=['precio_homecenter', 'precio_amazon', 'precio_mercadolibre'],
    title='Comparación de Precios Promedio por Canal',
    labels={'value': 'Precio Promedio ($)', 'variable': 'Canal', 'categoria': 'Categoría'},
    barmode='group'
)

fig_price_comparison.update_layout(
    height=600,
    margin=dict(l=0, r=0, t=40, b=0),
    xaxis_title='Categoría',
    yaxis_title='Precio Promedio ($)',
    showlegend=True
)

st.plotly_chart(fig_price_comparison, use_container_width=True)

# Mostrar diferencias porcentuales
col_price1, col_price2 = st.columns(2)

with col_price1:
    st.subheader('📈 Diferencias vs HomeCenter')
    
    # Gráfico de diferencias porcentuales
    fig_diff = px.bar(
        price_comparison,
        x='categoria',
        y=['diff_amazon_hc', 'diff_ml_hc'],
        title='Diferencias de Precio vs HomeCenter (%)',
        labels={'value': 'Diferencia (%)', 'variable': 'Canal', 'categoria': 'Categoría'},
        barmode='group'
    )
    
    fig_diff.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis_title='Categoría',
        yaxis_title='Diferencia (%)',
        showlegend=True
    )
    
    # Agregar línea de referencia en 0%
    fig_diff.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Precio HomeCenter")
    
    st.plotly_chart(fig_diff, use_container_width=True)

with col_price2:
    st.subheader('💰 Resumen de Precios por Canal')
    st.dataframe(
        price_comparison[['categoria', 'precio_homecenter', 'precio_amazon', 'precio_mercadolibre', 'diff_amazon_hc', 'diff_ml_hc']]
        .rename(columns={
            'categoria': 'Categoría',
            'precio_homecenter': 'HomeCenter',
            'precio_amazon': 'Amazon',
            'precio_mercadolibre': 'MercadoLibre',
            'diff_amazon_hc': 'Diff Amazon',
            'diff_ml_hc': 'Diff ML'
        })
        .style.format({
            'HomeCenter': '${:,.0f}',
            'Amazon': '${:,.0f}',
            'MercadoLibre': '${:,.0f}',
            'Diff Amazon': '{:+.1f}%',
            'Diff ML': '{:+.1f}%'
        }),
        use_container_width=True
    )
