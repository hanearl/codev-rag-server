package com.skax.library.model;

import jakarta.persistence.*;
import lombok.*;

import java.util.HashSet;
import java.util.Set;

@Entity
@Table(name = "books")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Book extends BaseEntity {
    @Column(nullable = false)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(nullable = false)
    private String isbn;

    @Column(name = "publication_year")
    private Integer publicationYear;

    @Column(nullable = false)
    private String author;

    @Column(name = "publisher")
    private String publisher;

    @Column(name = "total_copies", nullable = false)
    @Builder.Default
    private Integer totalCopies = 1;

    @Column(name = "available_copies", nullable = false)
    @Builder.Default
    private Integer availableCopies = 1;

    @Column(name = "cover_image_url")
    private String coverImageUrl;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    @Builder.Default
    private BookStatus status = BookStatus.AVAILABLE;

    @OneToMany(mappedBy = "book", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private Set<BookCategory> categories = new HashSet<>();

    @OneToMany(mappedBy = "book")
    @Builder.Default
    private Set<Loan> loans = new HashSet<>();

    @OneToMany(mappedBy = "book")
    @Builder.Default
    private Set<Reservation> reservations = new HashSet<>();

    public enum BookStatus {
        AVAILABLE, 
        ON_LOAN, 
        RESERVED, 
        LOST, 
        DAMAGED,
        UNDER_MAINTENANCE
    }
}
