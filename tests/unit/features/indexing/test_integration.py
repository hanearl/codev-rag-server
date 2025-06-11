"""Java 코드 파서 통합 테스트

실제 Java/Spring 코드 파일을 사용한 통합 테스트를 수행합니다.
"""

import pytest
from app.features.indexing.parsers.java_parser import JavaParser
from app.features.indexing.keyword_extractor import KeywordExtractor


class TestJavaParserIntegration:
    """Java 파서 통합 테스트 클래스"""
    
    def setup_method(self):
        """테스트 메소드 실행 전 설정"""
        self.parser = JavaParser()
    
    def test_parse_real_spring_controller_file(self):
        """실제 Spring Controller 파일 파싱 테스트"""
        # Given - 실제 Spring Boot Controller 파일
        spring_controller = '''
package com.example.ecommerce.controller;

import com.example.ecommerce.dto.ProductDto;
import com.example.ecommerce.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;

/**
 * 상품 관리 REST API Controller
 * 상품의 CRUD 작업을 처리합니다.
 */
@RestController
@RequestMapping("/api/v1/products")
@CrossOrigin(origins = "*")
public class ProductController {
    
    @Autowired
    private ProductService productService;
    
    /**
     * 모든 상품 목록을 조회합니다.
     * @return 상품 목록
     */
    @GetMapping
    public ResponseEntity<List<ProductDto>> getAllProducts() {
        List<ProductDto> products = productService.findAllProducts();
        return ResponseEntity.ok(products);
    }
    
    /**
     * ID로 특정 상품을 조회합니다.
     * @param productId 상품 ID
     * @return 상품 정보
     */
    @GetMapping("/{productId}")
    public ResponseEntity<ProductDto> getProductById(@PathVariable Long productId) {
        ProductDto product = productService.findProductById(productId);
        return ResponseEntity.ok(product);
    }
    
    /**
     * 새로운 상품을 등록합니다.
     * @param productDto 상품 정보
     * @return 생성된 상품 정보
     */
    @PostMapping
    public ResponseEntity<ProductDto> createProduct(@Valid @RequestBody ProductDto productDto) {
        ProductDto createdProduct = productService.createProduct(productDto);
        return ResponseEntity.status(HttpStatus.CREATED).body(createdProduct);
    }
    
    /**
     * 상품 정보를 수정합니다.
     * @param productId 상품 ID
     * @param productDto 수정할 상품 정보
     * @return 수정된 상품 정보
     */
    @PutMapping("/{productId}")
    public ResponseEntity<ProductDto> updateProduct(
            @PathVariable Long productId,
            @Valid @RequestBody ProductDto productDto) {
        ProductDto updatedProduct = productService.updateProduct(productId, productDto);
        return ResponseEntity.ok(updatedProduct);
    }
    
    /**
     * 상품을 삭제합니다.
     * @param productId 상품 ID
     * @return 삭제 결과
     */
    @DeleteMapping("/{productId}")
    public ResponseEntity<Void> deleteProduct(@PathVariable Long productId) {
        productService.deleteProduct(productId);
        return ResponseEntity.noContent().build();
    }
}
'''
        
        # When
        result = self.parser.parse_code(spring_controller, "ProductController.java")
        chunks = result.chunks
        
        # Then
        assert len(chunks) >= 6  # 클래스 1개 + 메소드 5개
        
        # Controller 클래스 검증
        controller_chunk = next((chunk for chunk in chunks if chunk.code_type.value == "class"), None)
        assert controller_chunk is not None
        assert controller_chunk.name == "ProductController"
        assert controller_chunk.language_specific.get("package_name") == "com.example.ecommerce.controller"
        assert "@RestController" in controller_chunk.language_specific.get("annotations", [])
        assert "@RequestMapping" in controller_chunk.language_specific.get("annotations", [])
        assert "product" in controller_chunk.keywords
        assert "controller" in controller_chunk.keywords
        assert "rest" in controller_chunk.keywords
        assert "api" in controller_chunk.keywords
        
        # CRUD 메소드들 검증
        method_names = [chunk.name for chunk in chunks if chunk.code_type.value == "method"]
        assert "ProductController.getAllProducts" in method_names
        assert "ProductController.getProductById" in method_names
        assert "ProductController.createProduct" in method_names
        assert "ProductController.updateProduct" in method_names
        assert "ProductController.deleteProduct" in method_names
        
        # GET 메소드 검증
        get_all_method = next((chunk for chunk in chunks if "getAllProducts" in chunk.name), None)
        assert get_all_method is not None
        assert "@GetMapping" in get_all_method.language_specific.get("annotations", [])
        assert "get" in get_all_method.keywords
        assert "product" in get_all_method.keywords
        
        # POST 메소드 검증
        create_method = next((chunk for chunk in chunks if "createProduct" in chunk.name), None)
        assert create_method is not None
        assert "@PostMapping" in create_method.language_specific.get("annotations", [])
        assert "create" in create_method.keywords
        assert "product" in create_method.keywords
    
    def test_parse_complex_jpa_entity_and_repository(self):
        """복잡한 JPA Entity와 Repository 파싱 테스트"""
        # Given - JPA Entity 파일
        jpa_entity = '''
package com.example.ecommerce.entity;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import javax.persistence.*;
import javax.validation.constraints.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 상품 엔티티
 * 이커머스 상품 정보를 저장하는 테이블과 매핑됩니다.
 */
@Entity
@Table(name = "products", indexes = {
    @Index(name = "idx_product_category", columnList = "category_id"),
    @Index(name = "idx_product_name", columnList = "product_name")
})
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Product {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "product_id")
    private Long productId;
    
    @NotBlank(message = "상품명은 필수입니다")
    @Size(max = 255, message = "상품명은 255자를 초과할 수 없습니다")
    @Column(name = "product_name", nullable = false)
    private String productName;
    
    @NotNull(message = "가격은 필수입니다")
    @DecimalMin(value = "0.0", inclusive = false, message = "가격은 0보다 커야 합니다")
    @Column(name = "price", nullable = false, precision = 10, scale = 2)
    private BigDecimal price;
    
    @Size(max = 1000, message = "설명은 1000자를 초과할 수 없습니다")
    @Column(name = "description", columnDefinition = "TEXT")
    private String description;
    
    @NotNull(message = "재고는 필수입니다")
    @Min(value = 0, message = "재고는 0 이상이어야 합니다")
    @Column(name = "stock_quantity", nullable = false)
    private Integer stockQuantity;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "category_id")
    private Category category;
    
    @OneToMany(mappedBy = "product", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<ProductImage> productImages;
    
    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
    
    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
    
    /**
     * 재고를 감소시킵니다.
     * @param quantity 감소할 수량
     * @throws IllegalArgumentException 재고가 부족한 경우
     */
    public void decreaseStock(Integer quantity) {
        if (this.stockQuantity < quantity) {
            throw new IllegalArgumentException("재고가 부족합니다");
        }
        this.stockQuantity -= quantity;
    }
    
    /**
     * 재고를 증가시킵니다.
     * @param quantity 증가할 수량
     */
    public void increaseStock(Integer quantity) {
        this.stockQuantity += quantity;
    }
    
    /**
     * 상품이 재고가 있는지 확인합니다.
     * @return 재고 여부
     */
    public boolean hasStock() {
        return this.stockQuantity > 0;
    }
}
'''
        
        # When
        result = self.parser.parse_code(jpa_entity, "Product.java")
        chunks = result.chunks
        
        # Then
        assert len(chunks) >= 4  # 클래스 1개 + 메소드 3개
        
        # Entity 클래스 검증
        entity_chunk = next((chunk for chunk in chunks if chunk.code_type.value == "class"), None)
        assert entity_chunk is not None
        assert entity_chunk.name == "Product"
        assert entity_chunk.language_specific.get("package_name") == "com.example.ecommerce.entity"
        assert "@Entity" in entity_chunk.language_specific.get("annotations", [])
        assert "@Table" in entity_chunk.language_specific.get("annotations", [])
        assert "@Data" in entity_chunk.language_specific.get("annotations", [])
        assert "product" in entity_chunk.keywords
        assert "entity" in entity_chunk.keywords
        
        # 비즈니스 메소드들 검증
        method_chunks = [chunk for chunk in chunks if chunk.code_type.value == "method"]
        method_names = [chunk.name for chunk in method_chunks]
        assert "Product.decreaseStock" in method_names
        assert "Product.increaseStock" in method_names
        assert "Product.hasStock" in method_names
        
        # decreaseStock 메소드 상세 검증
        decrease_method = next((chunk for chunk in chunks if "decreaseStock" in chunk.name), None)
        assert decrease_method is not None
        assert "decrease" in decrease_method.keywords
        assert "stock" in decrease_method.keywords
        assert decrease_method.language_specific.get("return_type") == "void"
    
    def test_parse_spring_service_with_complex_business_logic(self):
        """복잡한 비즈니스 로직을 가진 Spring Service 파싱 테스트"""
        # Given - Service 파일
        spring_service = '''
package com.example.ecommerce.service.impl;

import com.example.ecommerce.dto.OrderDto;
import com.example.ecommerce.dto.OrderItemDto;
import com.example.ecommerce.entity.Order;
import com.example.ecommerce.entity.OrderItem;
import com.example.ecommerce.entity.Product;
import com.example.ecommerce.entity.User;
import com.example.ecommerce.exception.InsufficientStockException;
import com.example.ecommerce.exception.ProductNotFoundException;
import com.example.ecommerce.exception.UserNotFoundException;
import com.example.ecommerce.repository.OrderRepository;
import com.example.ecommerce.repository.ProductRepository;
import com.example.ecommerce.repository.UserRepository;
import com.example.ecommerce.service.OrderService;
import com.example.ecommerce.service.PaymentService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 주문 처리 서비스
 * 주문 생성, 조회, 취소 등의 비즈니스 로직을 처리합니다.
 */
@Service
@RequiredArgsConstructor
@Slf4j
@Transactional(readOnly = true)
public class OrderServiceImpl implements OrderService {
    
    private final OrderRepository orderRepository;
    private final ProductRepository productRepository;
    private final UserRepository userRepository;
    private final PaymentService paymentService;
    
    /**
     * 새로운 주문을 생성합니다.
     * @param userId 사용자 ID
     * @param orderItemDtos 주문 상품 목록
     * @return 생성된 주문 정보
     * @throws UserNotFoundException 사용자를 찾을 수 없는 경우
     * @throws ProductNotFoundException 상품을 찾을 수 없는 경우
     * @throws InsufficientStockException 재고가 부족한 경우
     */
    @Override
    @Transactional
    public OrderDto createOrder(Long userId, List<OrderItemDto> orderItemDtos) {
        log.info("Creating order for user: {} with {} items", userId, orderItemDtos.size());
        
        // 사용자 조회
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException("사용자를 찾을 수 없습니다: " + userId));
        
        // 주문 생성
        Order order = Order.builder()
                .user(user)
                .orderDate(LocalDateTime.now())
                .status("PENDING")
                .build();
        
        BigDecimal totalAmount = BigDecimal.ZERO;
        
        // 주문 상품 처리
        for (OrderItemDto itemDto : orderItemDtos) {
            Product product = productRepository.findById(itemDto.getProductId())
                    .orElseThrow(() -> new ProductNotFoundException("상품을 찾을 수 없습니다: " + itemDto.getProductId()));
            
            // 재고 확인
            if (product.getStockQuantity() < itemDto.getQuantity()) {
                throw new InsufficientStockException("재고가 부족합니다. 상품: " + product.getProductName());
            }
            
            // 재고 감소
            product.decreaseStock(itemDto.getQuantity());
            
            // 주문 상품 생성
            OrderItem orderItem = OrderItem.builder()
                    .order(order)
                    .product(product)
                    .quantity(itemDto.getQuantity())
                    .price(product.getPrice())
                    .build();
            
            order.addOrderItem(orderItem);
            totalAmount = totalAmount.add(product.getPrice().multiply(BigDecimal.valueOf(itemDto.getQuantity())));
        }
        
        order.setTotalAmount(totalAmount);
        
        // 결제 처리
        boolean paymentSuccess = paymentService.processPayment(order.getTotalAmount(), user.getPaymentMethod());
        if (!paymentSuccess) {
            throw new RuntimeException("결제 처리에 실패했습니다");
        }
        
        order.setStatus("PAID");
        Order savedOrder = orderRepository.save(order);
        
        log.info("Order created successfully: {}", savedOrder.getOrderId());
        return convertToDto(savedOrder);
    }
    
    /**
     * 주문을 취소합니다.
     * @param orderId 주문 ID
     * @return 취소된 주문 정보
     */
    @Override
    @Transactional
    public OrderDto cancelOrder(Long orderId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new RuntimeException("주문을 찾을 수 없습니다: " + orderId));
        
        if (!"PAID".equals(order.getStatus())) {
            throw new RuntimeException("취소할 수 없는 주문 상태입니다: " + order.getStatus());
        }
        
        // 재고 복원
        for (OrderItem item : order.getOrderItems()) {
            item.getProduct().increaseStock(item.getQuantity());
        }
        
        order.setStatus("CANCELLED");
        Order savedOrder = orderRepository.save(order);
        
        return convertToDto(savedOrder);
    }
    
    /**
     * Order 엔티티를 DTO로 변환합니다.
     * @param order 주문 엔티티
     * @return 주문 DTO
     */
    private OrderDto convertToDto(Order order) {
        return OrderDto.builder()
                .orderId(order.getOrderId())
                .userId(order.getUser().getUserId())
                .orderDate(order.getOrderDate())
                .status(order.getStatus())
                .totalAmount(order.getTotalAmount())
                .orderItems(order.getOrderItems().stream()
                        .map(this::convertOrderItemToDto)
                        .collect(Collectors.toList()))
                .build();
    }
    
    /**
     * OrderItem 엔티티를 DTO로 변환합니다.
     * @param orderItem 주문 상품 엔티티
     * @return 주문 상품 DTO
     */
    private OrderItemDto convertOrderItemToDto(OrderItem orderItem) {
        return OrderItemDto.builder()
                .productId(orderItem.getProduct().getProductId())
                .productName(orderItem.getProduct().getProductName())
                .quantity(orderItem.getQuantity())
                .price(orderItem.getPrice())
                .build();
    }
}
'''
        
        # When
        result = self.parser.parse_code(spring_service, "OrderServiceImpl.java")
        chunks = result.chunks
        
        # Then
        assert len(chunks) >= 5  # 클래스 1개 + 메소드 4개
        
        # Service 클래스 검증
        service_chunk = next((chunk for chunk in chunks if chunk.code_type.value == "class"), None)
        assert service_chunk is not None
        assert service_chunk.name == "OrderServiceImpl"
        assert service_chunk.language_specific.get("package_name") == "com.example.ecommerce.service.impl"
        assert "@Service" in service_chunk.language_specific.get("annotations", [])
        assert "@RequiredArgsConstructor" in service_chunk.language_specific.get("annotations", [])
        assert "@Transactional" in service_chunk.language_specific.get("annotations", [])
        assert "order" in service_chunk.keywords
        assert "service" in service_chunk.keywords
        
        # 비즈니스 메소드들 검증
        method_chunks = [chunk for chunk in chunks if chunk.code_type.value == "method"]
        method_names = [chunk.name for chunk in method_chunks]
        assert "OrderServiceImpl.createOrder" in method_names
        assert "OrderServiceImpl.cancelOrder" in method_names
        assert "OrderServiceImpl.convertToDto" in method_names
        assert "OrderServiceImpl.convertOrderItemToDto" in method_names
        
        # createOrder 메소드 상세 검증
        create_order_method = next((chunk for chunk in chunks if "createOrder" in chunk.name), None)
        assert create_order_method is not None
        assert "@Transactional" in create_order_method.language_specific.get("annotations", [])
        assert "create" in create_order_method.keywords
        assert "order" in create_order_method.keywords
        assert create_order_method.language_specific.get("return_type") == "OrderDto"
        
        # 모든 청크가 올바른 메타데이터를 가지는지 확인
        for chunk in chunks:
            assert chunk.language_specific.get("package_name") == "com.example.ecommerce.service.impl"
            assert chunk.file_path == "OrderServiceImpl.java"
            assert chunk.line_start > 0
            assert chunk.line_end >= chunk.line_start
            assert len(chunk.keywords) > 0 