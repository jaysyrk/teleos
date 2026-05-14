package io.teleos;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class EngineTest {

    private static final String RULES =
            "fact: alice is admin\n" +
            "fact: bob is user\n" +
            "fact: charlie is user\n" +
            "fact: charlie is banned\n" +
            "fact: report is public\n" +
            "fact: document is confidential\n" +
            "rule: if X is admin then X can access Y\n" +
            "rule: if X is user and Y is public and not X is banned then X can access Y\n";

    private static final String GRADES =
            "fact: alice score 95\n" +
            "fact: bob score 80\n" +
            "fact: charlie score 65\n" +
            "rule: if X score S and S > 90 then X gets distinction\n" +
            "rule: if X score S and S > 75 and S <= 90 then X gets merit\n" +
            "rule: if X score S and S > 60 and S <= 75 then X gets pass\n" +
            "rule: if X score S and S <= 60 then X gets fail\n";

    @Test
    void testAskTrue() throws Exception {
        try (Engine e = Engine.parse(RULES)) {
            assertTrue(e.ask("alice can access document"));
        }
    }

    @Test
    void testAskFalse() throws Exception {
        try (Engine e = Engine.parse(RULES)) {
            assertFalse(e.ask("bob can access document"));
        }
    }

    @Test
    void testNegation() throws Exception {
        try (Engine e = Engine.parse(RULES)) {
            assertTrue(e.ask("bob can access report"));
            assertFalse(e.ask("charlie can access report"));
        }
    }

    @Test
    void testWhy() throws Exception {
        try (Engine e = Engine.parse(RULES)) {
            String why = e.why("bob can access report");
            assertTrue(why.contains("bob is user"), "why should contain 'bob is user', got: " + why);
        }
    }

    @Test
    void testWhyFail() throws Exception {
        try (Engine e = Engine.parse(RULES)) {
            String why = e.why("charlie can access document");
            assertTrue(why.contains("Cannot prove") || why.toLowerCase().contains("cannot prove"),
                    "why failure should say Cannot prove, got: " + why);
        }
    }

    @Test
    void testAll() throws Exception {
        try (Engine e = Engine.parse(RULES)) {
            List<String> results = e.all("WHO can access document");
            assertTrue(results.stream().anyMatch(r -> r.contains("alice")),
                    "alice should be able to access document");
            assertTrue(results.stream().noneMatch(r -> r.contains("charlie")),
                    "charlie should not be able to access document");
        }
    }

    @Test
    void testAddFact() throws Exception {
        try (Engine e = Engine.parse(RULES)) {
            assertFalse(e.ask("dave can access document"));
            e.addFact("dave is admin");
            assertTrue(e.ask("dave can access document"));
        }
    }

    @Test
    void testNumericDistinction() throws Exception {
        try (Engine e = Engine.parse(GRADES)) {
            assertTrue(e.ask("alice gets distinction"));
            assertFalse(e.ask("alice gets fail"));
        }
    }

    @Test
    void testNumericMerit() throws Exception {
        try (Engine e = Engine.parse(GRADES)) {
            assertTrue(e.ask("bob gets merit"));
            assertFalse(e.ask("bob gets distinction"));
        }
    }

    @Test
    void testNumericPass() throws Exception {
        try (Engine e = Engine.parse(GRADES)) {
            assertTrue(e.ask("charlie gets pass"));
        }
    }
}
