package com.skax.library.controller;

import com.skax.library.dto.LoanDto;
import com.skax.library.dto.MemberDto;
import com.skax.library.dto.ReservationDto;
import com.skax.library.model.Member;
import com.skax.library.service.LoanService;
import com.skax.library.service.MemberService;
import com.skax.library.service.ReservationService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/members")
@Tag(name = "Member Management", description = "APIs for managing library members")
@RequiredArgsConstructor
public class MemberController {
    private final MemberService memberService;
    private final LoanService loanService;
    private final ReservationService reservationService;

    @PostMapping
    @Operation(summary = "Register a new member")
    public ResponseEntity<MemberDto> registerMember(@Valid @RequestBody MemberDto memberDto) {
        MemberDto createdMember = memberService.createMember(memberDto);
        return new ResponseEntity<>(createdMember, HttpStatus.CREATED);
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update a member by ID")
    public ResponseEntity<MemberDto> updateMember(
            @Parameter(description = "ID of the member to be updated")
            @PathVariable Long id,
            @Valid @RequestBody MemberDto memberDto) {
        MemberDto updatedMember = memberService.updateMember(id, memberDto);
        return ResponseEntity.ok(updatedMember);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get a member by ID")
    public ResponseEntity<MemberDto> getMemberById(
            @Parameter(description = "ID of the member to be retrieved")
            @PathVariable Long id) {
        MemberDto memberDto = memberService.getMemberById(id);
        return ResponseEntity.ok(memberDto);
    }

    @GetMapping
    @Operation(summary = "Get all members with pagination")
    public ResponseEntity<Page<MemberDto>> getAllMembers(
            @PageableDefault(size = 20) Pageable pageable,
            @Parameter(description = "Search query for member name or email")
            @RequestParam(required = false) String search) {
        Page<MemberDto> members;
        if (search != null && !search.trim().isEmpty()) {
            members = memberService.searchMembers(search, pageable);
        } else {
            members = memberService.getAllMembers(pageable);
        }
        return ResponseEntity.ok(members);
    }

    @GetMapping("/active")
    @Operation(summary = "Get all active members")
    public ResponseEntity<List<MemberDto>> getActiveMembers() {
        List<MemberDto> activeMembers = memberService.getActiveMembers();
        return ResponseEntity.ok(activeMembers);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete a member by ID")
    public ResponseEntity<Void> deleteMember(
            @Parameter(description = "ID of the member to be deleted")
            @PathVariable Long id) {
        memberService.deleteMember(id);
        return ResponseEntity.noContent().build();
    }

    @PutMapping("/{id}/status")
    @Operation(summary = "Update member status")
    public ResponseEntity<MemberDto> updateMemberStatus(
            @Parameter(description = "ID of the member to update status for")
            @PathVariable Long id,
            @Parameter(description = "New status for the member")
            @RequestParam Member.MemberStatus status) {
        MemberDto updatedMember = memberService.updateMemberStatus(id, status);
        return ResponseEntity.ok(updatedMember);
    }

    @GetMapping("/{memberId}/loans")
    @Operation(summary = "Get all loans for a member")
    public ResponseEntity<List<LoanDto>> getMemberLoans(
            @Parameter(description = "ID of the member to get loans for")
            @PathVariable Long memberId,
            @Parameter(description = "Filter for active loans only")
            @RequestParam(required = false) Boolean active) {
        List<LoanDto> loans;
        if (active != null && active) {
            loans = loanService.getActiveLoansByMemberId(memberId);
        } else {
            loans = loanService.getLoansByMemberId(memberId);
        }
        return ResponseEntity.ok(loans);
    }

    @GetMapping("/{memberId}/reservations")
    @Operation(summary = "Get all reservations for a member")
    public ResponseEntity<List<ReservationDto>> getMemberReservations(
            @Parameter(description = "ID of the member to get reservations for")
            @PathVariable Long memberId,
            @Parameter(description = "Filter for active reservations only")
            @RequestParam(required = false) Boolean active) {
        List<ReservationDto> reservations;
        if (active != null && active) {
            reservations = reservationService.getActiveReservationsByMemberId(memberId);
        } else {
            reservations = reservationService.getReservationsByMemberId(memberId);
        }
        return ResponseEntity.ok(reservations);
    }
}
