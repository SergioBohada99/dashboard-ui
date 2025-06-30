# augment_sales.py  (versión mejorada con satisfacción y precios por canal)

import pandas as pd
import numpy as np

df = pd.read_csv("data.csv", sep="\t", encoding="latin1")
df["fecha_venta"] = pd.to_datetime(df["fecha_venta"], dayfirst=True, errors="coerce")

# Agregar satisfacción del cliente (puntaje 1-5)
def generate_satisfaction_score():
    """Genera puntajes de satisfacción realistas basados en distribución normal"""
    # 70% de clientes satisfechos (4-5), 20% neutral (3), 10% insatisfechos (1-2)
    weights = [0.05, 0.05, 0.20, 0.40, 0.30]  # Probabilidades para puntajes 1-5
    return np.random.choice([1, 2, 3, 4, 5], size=len(df), p=weights)

df["satisfaccion_cliente"] = generate_satisfaction_score()

# Agregar precios por canal de venta
def generate_channel_prices():
    """Genera precios para diferentes canales con variaciones realistas"""
    base_prices = df["precio"].values
    
    # HomeCenter (precio base)
    homecenter_prices = base_prices
    
    # Amazon (generalmente 5-15% más barato)
    amazon_discount = np.random.uniform(0.05, 0.15, len(df))
    amazon_prices = base_prices * (1 - amazon_discount)
    
    # MercadoLibre (puede ser más barato o más caro, variación -10% a +20%)
    ml_variation = np.random.uniform(-0.10, 0.20, len(df))
    mercadolibre_prices = base_prices * (1 + ml_variation)
    
    return homecenter_prices, amazon_prices, mercadolibre_prices

homecenter_prices, amazon_prices, mercadolibre_prices = generate_channel_prices()

df["precio_homecenter"] = homecenter_prices
df["precio_amazon"] = amazon_prices
df["precio_mercadolibre"] = mercadolibre_prices

# Agregar disponibilidad por canal
def generate_channel_availability():
    """Genera disponibilidad realista por canal"""
    availability_options = ["Disponible", "Consultar", "Agotado", "Envío 24h"]
    weights = [0.60, 0.25, 0.10, 0.05]  # Probabilidades
    
    homecenter_avail = np.random.choice(availability_options, size=len(df), p=weights)
    amazon_avail = np.random.choice(availability_options, size=len(df), p=[0.70, 0.20, 0.05, 0.05])
    ml_avail = np.random.choice(availability_options, size=len(df), p=[0.65, 0.25, 0.05, 0.05])
    
    return homecenter_avail, amazon_avail, ml_avail

homecenter_avail, amazon_avail, mercadolibre_avail = generate_channel_availability()

df["disponibilidad_homecenter"] = homecenter_avail
df["disponibilidad_amazon"] = amazon_avail
df["disponibilidad_mercadolibre"] = mercadolibre_avail

# Agregar calificaciones por canal
def generate_channel_ratings():
    """Genera calificaciones de productos por canal"""
    # Calificaciones de 1-5 estrellas
    homecenter_ratings = np.random.normal(4.2, 0.8, len(df)).clip(1, 5)
    amazon_ratings = np.random.normal(4.4, 0.7, len(df)).clip(1, 5)
    ml_ratings = np.random.normal(4.0, 0.9, len(df)).clip(1, 5)
    
    return homecenter_ratings, amazon_ratings, ml_ratings

homecenter_ratings, amazon_ratings, ml_ratings = generate_channel_ratings()

df["calificacion_homecenter"] = homecenter_ratings.round(1)
df["calificacion_amazon"] = amazon_ratings.round(1)
df["calificacion_mercadolibre"] = ml_ratings.round(1)

# Generar datos aumentados
augments = []
for offset in range(1, 6):        # 5 meses extra
    tmp = df.copy()
    tmp["fecha_venta"] = tmp["fecha_venta"] + pd.DateOffset(months=offset)
    tmp["fecha_venta"] += pd.to_timedelta(
        np.random.randint(0, 28, size=len(tmp)), unit="D"
    )
    
    # Variar ligeramente los precios y satisfacción en el tiempo
    price_variation = np.random.uniform(0.95, 1.05, len(tmp))
    tmp["precio"] = tmp["precio"] * price_variation
    tmp["precio_homecenter"] = tmp["precio_homecenter"] * price_variation
    tmp["precio_amazon"] = tmp["precio_amazon"] * price_variation
    tmp["precio_mercadolibre"] = tmp["precio_mercadolibre"] * price_variation
    
    # Regenerar satisfacción para variar en el tiempo
    tmp["satisfaccion_cliente"] = generate_satisfaction_score()
    
    augments.append(tmp)

df_aug = pd.concat([df] + augments, ignore_index=True)

# Asegurar que los precios sean positivos
price_columns = ["precio", "precio_homecenter", "precio_amazon", "precio_mercadolibre"]
for col in price_columns:
    df_aug[col] = df_aug[col].clip(lower=1000)  # Precio mínimo de $1,000

df_aug.to_csv("data_aug.csv", sep="\t", index=False, encoding="latin1")

print("✅ Generado data_aug.csv con", len(df_aug), "filas")
print("📊 Nuevas columnas agregadas:")
print("   - satisfaccion_cliente (1-5)")
print("   - precio_homecenter, precio_amazon, precio_mercadolibre")
print("   - disponibilidad_homecenter, disponibilidad_amazon, disponibilidad_mercadolibre")
print("   - calificacion_homecenter, calificacion_amazon, calificacion_mercadolibre")
