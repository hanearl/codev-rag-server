package com.skax.library.dto;

import com.skax.library.model.Member;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Pattern;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;

@Getter
@Setter
public class MemberDto extends BaseDto {
    @NotBlank(message = "First name is required")
    private String firstName;
    
    @NotBlank(message = "Last name is required")
    private String lastName;
    
    @NotBlank(message = "Email is required")
    @Email(message = "Invalid email format")
    private String email;
    
    @Pattern(regexp = "^[0-9\\-\\+]{9,15}$", message = "Invalid phone number format")
    private String phoneNumber;
    
    @NotBlank(message = "Address is required")
    private String address;
    
    @Past(message = "Date of birth must be in the past")
    private LocalDate dateOfBirth;
    
    private LocalDate membershipStartDate;
    private LocalDate membershipEndDate;
    private Member.MemberStatus status;
    private Integer maxBooksAllowed;
    
    // For responses
    private Integer borrowedBooksCount;
    private Integer activeReservationsCount;
    private Double totalFines;
    
    public static MemberDto fromEntity(Member member) {
        if (member == null) {
            return null;
        }
        
        MemberDto dto = new MemberDto();
        dto.setId(member.getId());
        dto.setFirstName(member.getFirstName());
        dto.setLastName(member.getLastName());
        dto.setEmail(member.getEmail());
        dto.setPhoneNumber(member.getPhoneNumber());
        dto.setAddress(member.getAddress());
        dto.setDateOfBirth(member.getDateOfBirth());
        dto.setMembershipStartDate(member.getMembershipStartDate());
        dto.setMembershipEndDate(member.getMembershipEndDate());
        dto.setStatus(member.getStatus());
        dto.setMaxBooksAllowed(member.getMaxBooksAllowed());
        dto.setCreatedAt(member.getCreatedAt());
        dto.setUpdatedAt(member.getUpdatedAt());
        
        return dto;
    }
    
    public Member toEntity() {
        Member member = new Member();
        member.setFirstName(this.firstName);
        member.setLastName(this.lastName);
        member.setEmail(this.email);
        member.setPhoneNumber(this.phoneNumber);
        member.setAddress(this.address);
        member.setDateOfBirth(this.dateOfBirth);
        member.setMembershipStartDate(this.membershipStartDate != null ? this.membershipStartDate : LocalDate.now());
        member.setMembershipEndDate(this.membershipEndDate);
        member.setStatus(this.status != null ? this.status : Member.MemberStatus.ACTIVE);
        member.setMaxBooksAllowed(this.maxBooksAllowed != null ? this.maxBooksAllowed : 5);
        
        return member;
    }
    
    public String getFullName() {
        return String.format("%s %s", firstName, lastName);
    }
}
