package com.skax.library.dto;

import com.skax.library.model.Book;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import lombok.Getter;
import lombok.Setter;

import java.util.HashSet;
import java.util.Set;

@Getter
@Setter
public class BookDto extends BaseDto {
    @NotBlank(message = "Title is required")
    private String title;
    
    private String description;
    
    @NotBlank(message = "ISBN is required")
    private String isbn;
    
    private Integer publicationYear;
    
    @NotBlank(message = "Author is required")
    private String author;
    
    private String publisher;
    
    @NotNull(message = "Total copies is required")
    @PositiveOrZero(message = "Total copies must be zero or positive")
    private Integer totalCopies;
    
    private Integer availableCopies;
    
    private String coverImageUrl;
    
    private Book.BookStatus status;
    
    private Set<CategoryDto> categories = new HashSet<>();
    
    // For responses
    private Long categoryCount;
    
    public static BookDto fromEntity(Book book) {
        if (book == null) {
            return null;
        }
        
        BookDto dto = new BookDto();
        dto.setId(book.getId());
        dto.setTitle(book.getTitle());
        dto.setDescription(book.getDescription());
        dto.setIsbn(book.getIsbn());
        dto.setPublicationYear(book.getPublicationYear());
        dto.setAuthor(book.getAuthor());
        dto.setPublisher(book.getPublisher());
        dto.setTotalCopies(book.getTotalCopies());
        dto.setAvailableCopies(book.getAvailableCopies());
        dto.setCoverImageUrl(book.getCoverImageUrl());
        dto.setStatus(book.getStatus());
        dto.setCreatedAt(book.getCreatedAt());
        dto.setUpdatedAt(book.getUpdatedAt());
        
        if (book.getCategories() != null) {
            book.getCategories().forEach(bookCategory -> 
                dto.getCategories().add(CategoryDto.fromEntity(bookCategory.getCategory()))
            );
            dto.setCategoryCount((long) book.getCategories().size());
        }
        
        return dto;
    }
    
    public Book toEntity() {
        Book book = new Book();
        book.setTitle(this.title);
        book.setDescription(this.description);
        book.setIsbn(this.isbn);
        book.setPublicationYear(this.publicationYear);
        book.setAuthor(this.author);
        book.setPublisher(this.publisher);
        book.setTotalCopies(this.totalCopies != null ? this.totalCopies : 1);
        book.setAvailableCopies(this.availableCopies != null ? this.availableCopies : book.getTotalCopies());
        book.setCoverImageUrl(this.coverImageUrl);
        book.setStatus(this.status != null ? this.status : Book.BookStatus.AVAILABLE);
        
        return book;
    }
}
