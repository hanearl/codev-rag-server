package com.skax.library.service.impl;

import com.skax.library.dto.BookDto;
import com.skax.library.exception.ResourceNotFoundException;
import com.skax.library.mapper.BookMapper;
import com.skax.library.model.*;
import com.skax.library.repository.BookRepository;
import com.skax.library.repository.CategoryRepository;
import com.skax.library.service.BookService;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class BookServiceImpl implements BookService {
    private final BookRepository bookRepository;
    private final CategoryRepository categoryRepository;
    private final BookMapper bookMapper;

    @Override
    @Transactional
    public BookDto createBook(BookDto bookDto, List<Long> categoryIds) {
        if (bookRepository.existsByIsbn(bookDto.getIsbn())) {
            throw new IllegalStateException("Book with ISBN " + bookDto.getIsbn() + " already exists");
        }
        
        Book book = bookMapper.toEntity(bookDto);
        Book savedBook = bookRepository.save(book);
        
        if (categoryIds != null && !categoryIds.isEmpty()) {
            addCategoriesToBook(savedBook.getId(), categoryIds);
        }
        
        return bookMapper.toDto(savedBook);
    }

    @Override
    @Transactional
    public BookDto updateBook(Long id, BookDto bookDto, List<Long> categoryIds) {
        Book existingBook = bookRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Book not found with id: " + id));
        
        if (!existingBook.getIsbn().equals(bookDto.getIsbn()) && 
            bookRepository.existsByIsbn(bookDto.getIsbn())) {
            throw new IllegalStateException("Another book with ISBN " + bookDto.getIsbn() + " already exists");
        }
        
        // Update book fields from DTO
        bookMapper.updateBookFromDto(bookDto, existingBook);
        
        // Update categories if provided
        if (categoryIds != null) {
            // Remove existing categories
            existingBook.getCategories().clear();
            bookRepository.save(existingBook);
            
            // Add new categories
            if (!categoryIds.isEmpty()) {
                addCategoriesToBook(id, categoryIds);
            }
        }
        
        Book updatedBook = bookRepository.save(existingBook);
        return bookMapper.toDto(updatedBook);
    }

    @Override
    public BookDto getBookById(Long id) {
        Book book = bookRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Book not found with id: " + id));
        return bookMapper.toDto(book);
    }

    @Override
    public BookDto getBookByIsbn(String isbn) {
        Book book = bookRepository.findByIsbn(isbn)
                .orElseThrow(() -> new ResourceNotFoundException("Book not found with ISBN: " + isbn));
        return bookMapper.toDto(book);
    }

    @Override
    public Page<BookDto> getAllBooks(Pageable pageable) {
        return bookRepository.findAll(pageable)
                .map(bookMapper::toDto);
    }

    @Override
    public Page<BookDto> searchBooks(String query, Pageable pageable) {
        return bookRepository.findAll((root, query1, criteriaBuilder) -> {
            if (query == null || query.trim().isEmpty()) {
                return criteriaBuilder.conjunction();
            }
            String searchTerm = "%" + query.toLowerCase() + "%";
            return criteriaBuilder.or(
                criteriaBuilder.like(criteriaBuilder.lower(root.get("title")), searchTerm),
                criteriaBuilder.like(criteriaBuilder.lower(root.get("author")), searchTerm),
                criteriaBuilder.like(criteriaBuilder.lower(root.get("isbn")), query.toLowerCase())
            );
        }, pageable).map(bookMapper::toDto);
    }

    @Override
    public List<BookDto> getBooksByCategory(Long categoryId) {
        return bookRepository.findByCategories_CategoryId(categoryId).stream()
                .map(bookMapper::toDto)
                .collect(Collectors.toList());
    }

    @Override
    public List<BookDto> getAvailableBooks() {
        return bookRepository.findAvailableBooks().stream()
                .map(bookMapper::toDto)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void deleteBook(Long id) {
        Book book = bookRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Book not found with id: " + id));
                
        if (book.getAvailableCopies() < book.getTotalCopies()) {
            throw new IllegalStateException("Cannot delete book with active loans");
        }
        
        bookRepository.delete(book);
    }

    @Override
    @Transactional
    public BookDto updateBookStatus(Long id, Book.BookStatus status) {
        Book book = bookRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Book not found with id: " + id));
                
        book.setStatus(status);
        Book updatedBook = bookRepository.save(book);
        return bookMapper.toDto(updatedBook);
    }

    @Override
    @Transactional
    public BookDto addCategoriesToBook(Long bookId, List<Long> categoryIds) {
        Book book = bookRepository.findById(bookId)
                .orElseThrow(() -> new ResourceNotFoundException("Book not found with id: " + bookId));
                
        Set<BookCategory> existingCategories = book.getCategories();
        
        categoryIds.forEach(categoryId -> {
            Category category = categoryRepository.findById(categoryId)
                    .orElseThrow(() -> new ResourceNotFoundException("Category not found with id: " + categoryId));
            
            boolean categoryExists = existingCategories.stream()
                    .anyMatch(bc -> bc.getCategory().getId().equals(categoryId));
                    
            if (!categoryExists) {
                BookCategory bookCategory = BookCategory.builder()
                        .book(book)
                        .category(category)
                        .isPrimary(false)
                        .build();
                existingCategories.add(bookCategory);
            }
        });
        
        Book updatedBook = bookRepository.save(book);
        return bookMapper.toDto(updatedBook);
    }

    @Override
    @Transactional
    public BookDto removeCategoryFromBook(Long bookId, Long categoryId) {
        Book book = bookRepository.findById(bookId)
                .orElseThrow(() -> new ResourceNotFoundException("Book not found with id: " + bookId));
        
        boolean removed = book.getCategories().removeIf(
            bc -> bc.getCategory().getId().equals(categoryId)
        );
        
        if (!removed) {
            throw new ResourceNotFoundException("Category " + categoryId + " not found for book " + bookId);
        }
        
        Book updatedBook = bookRepository.save(book);
        return bookMapper.toDto(updatedBook);
    }

    public Page<BookDto> findAll(Specification<Book> spec, Pageable pageable) {
        return bookRepository.findAll(spec, pageable)
                .map(bookMapper::toDto);
    }
}
