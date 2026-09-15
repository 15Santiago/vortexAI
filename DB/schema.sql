CREATE DATABASE IF NOT EXISTS vortexai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE vortexai;

CREATE TABLE roles (
    id TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE,
    description VARCHAR(255) NULL
) ENGINE = InnoDB;

INSERT INTO roles (name, description)
VALUES
    ('usuario', 'Puede consultar el catalogo y sus estadisticas'),
    ('administrador', 'Puede administrar usuarios y catalogo')
ON DUPLICATE KEY UPDATE description = VALUES(description);

CREATE TABLE users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role_id TINYINT UNSIGNED NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    username VARCHAR(50) NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_role
        FOREIGN KEY (role_id) REFERENCES roles (id)
) ENGINE = InnoDB;

CREATE TABLE categories (
    id SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
) ENGINE = InnoDB;

CREATE TABLE products (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_key CHAR(64) NOT NULL UNIQUE,
    asin CHAR(10) NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    category_id SMALLINT UNSIGNED NOT NULL,
    product_page_url TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id) REFERENCES categories (id),
    INDEX idx_products_category (category_id),
    FULLTEXT INDEX ft_products_title (title)
) ENGINE = InnoDB;

CREATE TABLE product_images (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT UNSIGNED NOT NULL,
    image_url TEXT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE KEY uq_product_image (product_id, image_url(255)),
    CONSTRAINT fk_product_images_product
        FOREIGN KEY (product_id) REFERENCES products (id)
        ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE TABLE product_observations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT UNSIGNED NOT NULL,
    collected_at DATETIME NOT NULL,
    rating DECIMAL(2,1) NULL,
    total_reviews INT UNSIGNED NULL,
    purchased_last_month INT UNSIGNED NULL,
    discounted_price DECIMAL(10,2) NULL,
    original_price DECIMAL(10,2) NULL,
    discount_percentage DECIMAL(5,2) NULL,
    seller_badge VARCHAR(100) NULL,
    is_sponsored BOOLEAN NOT NULL DEFAULT FALSE,
    coupon_text VARCHAR(255) NULL,
    buy_box_availability VARCHAR(100) NULL,
    delivery_date DATE NULL,
    sustainability_tag VARCHAR(100) NULL,
    source_url TEXT NULL,
    CONSTRAINT fk_product_observations_product
        FOREIGN KEY (product_id) REFERENCES products (id)
        ON DELETE CASCADE,
    CONSTRAINT chk_observations_rating
        CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    CONSTRAINT chk_observations_discount
        CHECK (discount_percentage IS NULL OR (discount_percentage >= 0 AND discount_percentage <= 100)),
    INDEX idx_observations_product_date (product_id, collected_at),
    INDEX idx_observations_collected_at (collected_at)
) ENGINE = InnoDB;