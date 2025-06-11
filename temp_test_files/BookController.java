package com.skax.library.controller;

import com.skax.library.dto.BookDto;
import com.skax.library.dto.CategoryDto;
import com.skax.library.model.Book;
import com.skax.library.service.BookService;
import com.skax.library.service.CategoryService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/books")
@Tag(name = "Book Management", description = "APIs for managing books")
public class BookController {
    private final BookService bookService;
    private final CategoryService categoryService;

    public BookController(BookService bookService, CategoryService categoryService) {
        this.bookService = bookService;
        this.categoryService = categoryService;
    }

    @PostMapping
    @Operation(summary = "Create a new book")
    public ResponseEntity<BookDto> createBook(
            @Valid @RequestBody BookDto bookDto,
            @RequestParam(required = false) List<Long> categoryIds) {
        BookDto createdBook = bookService.createBook(bookDto, categoryIds);
        return new ResponseEntity<>(createdBook, HttpStatus.CREATED);
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update a book by ID")
    public ResponseEntity<BookDto> updateBook(
            @PathVariable Long id,
            @Valid @RequestBody BookDto bookDto,
            @RequestParam(required = false) List<Long> categoryIds) {
        bookDto.setId(id);
        BookDto updatedBook = bookService.updateBook(id, bookDto, categoryIds);
        return ResponseEntity.ok(updatedBook);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get a book by ID")
    public ResponseEntity<BookDto> getBookById(
            @Parameter(description = "ID of the book to be retrieved") 
            @PathVariable Long id) {
        BookDto bookDto = bookService.getBookById(id);
        return ResponseEntity.ok(bookDto);
    }

    @GetMapping
    @Operation(summary = "Get all books with pagination")
    public ResponseEntity<Page<BookDto>> getAllBooks(
            @PageableDefault(size = 10) Pageable pageable,
            @RequestParam(required = false) String search) {
        Page<BookDto> books;
        if (search != null && !search.trim().isEmpty()) {
            books = bookService.searchBooks(search, pageable);
        } else {
            books = bookService.getAllBooks(pageable);
        }
        return ResponseEntity.ok(books);
    }

    @GetMapping("/available")
    @Operation(summary = "Get all available books")
    public ResponseEntity<List<BookDto>> getAvailableBooks() {
        List<BookDto> books = bookService.getAvailableBooks();
        return ResponseEntity.ok(books);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete a book by ID")
    public ResponseEntity<Void> deleteBook(
            @Parameter(description = "ID of the book to be deleted") 
            @PathVariable Long id) {
        bookService.deleteBook(id);
        return ResponseEntity.noContent().build();
    }

    @PutMapping("/{id}/status")
    @Operation(summary = "Update book status")
    public ResponseEntity<BookDto> updateBookStatus(
            @PathVariable Long id,
            @RequestParam Book.BookStatus status) {
        BookDto updatedBook = bookService.updateBookStatus(id, status);
        return ResponseEntity.ok(updatedBook);
    }

    @PostMapping("/{bookId}/categories")
    @Operation(summary = "Add categories to a book")
    public ResponseEntity<BookDto> addCategoriesToBook(
            @PathVariable Long bookId,
            @RequestParam List<Long> categoryIds) {
        BookDto updatedBook = bookService.addCategoriesToBook(bookId, categoryIds);
        return ResponseEntity.ok(updatedBook);
    }

    @DeleteMapping("/{bookId}/categories/{categoryId}")
    @Operation(summary = "Remove a category from a book")
    public ResponseEntity<BookDto> removeCategoryFromBook(
            @PathVariable Long bookId,
            @PathVariable Long categoryId) {
        BookDto updatedBook = bookService.removeCategoryFromBook(bookId, categoryId);
        return ResponseEntity.ok(updatedBook);
    }

    @GetMapping("/{bookId}/categories")
    @Operation(summary = "Get all categories for a book")
    public ResponseEntity<List<CategoryDto>> getBookCategories(@PathVariable Long bookId) {
        List<CategoryDto> categories = categoryService.getCategoriesByBookId(bookId);
        return ResponseEntity.ok(categories);
    }
} 