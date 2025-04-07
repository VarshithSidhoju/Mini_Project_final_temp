import streamlit as st
from typing import List, Dict

def analyze_performance():
    """Calculate test results with accurate scoring"""
    if not st.session_state.get('test_completed', False):
        st.warning("Complete the test first!")
        return
    
    # Initialize counters
    correct_mcqs = 0
    total_mcqs = 0
    correct_short = 0.0
    total_short = 0
    correct_answers = []
    incorrect_answers = []

    for q in st.session_state.questions:
        # Get and clean the user's answer
        user_answer = str(st.session_state.user_answers.get(q["question"], "")).strip()
        correct_answer = str(q["answer"]).strip()
        
        if q["type"] == "MCQ":
            total_mcqs += 1
            # Compare selected option value with correct answer
            if user_answer == correct_answer:
                correct_mcqs += 1
                correct_answers.append({
                    "question": q["question"],
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "explanation": q.get("explanation", ""),
                    "type": "MCQ"
                })
            else:
                incorrect_answers.append({
                    "question": q["question"],
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "explanation": q.get("explanation", ""),
                    "type": "MCQ"
                })
                
        else:  # Short Answer
            total_short += 1
            keywords = [str(kw).strip().lower() for kw in q.get("keywords", [])]
            user_answer_lower = user_answer.lower()
            
            # Check if we should use keyword matching or direct comparison
            if keywords:
                # Keyword-based scoring
                matched = sum(1 for kw in keywords if kw in user_answer_lower)
                score = matched / len(keywords)
                is_correct = score >= 0.6  # 60% match threshold
            else:
                # Direct answer comparison if no keywords
                is_correct = user_answer_lower == correct_answer.lower()
                score = 1.0 if is_correct else 0.0
            
            # Record answer details
            answer_data = {
                "question": q["question"],
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "explanation": q.get("explanation", ""),
                "score": score,
                "matched_keywords": matched if keywords else 0,
                "total_keywords": len(keywords) if keywords else 0,
                "type": "Short Answer"
            }
            
            if is_correct:
                correct_short += score if keywords else 1.0
                correct_answers.append(answer_data)
            else:
                incorrect_answers.append(answer_data)
    
    # Calculate final scores
    total_score = correct_mcqs + correct_short
    total_questions = len(st.session_state.questions)
    accuracy = (total_score / total_questions) * 100 if total_questions > 0 else 0
    
    # Debug output - remove after testing
    st.write("Debug Info:")
    st.write(f"MCQs: {correct_mcqs}/{total_mcqs}")
    st.write(f"Short Answers: {correct_short}/{total_short}")
    st.write(f"User Answers: {st.session_state.user_answers}")
    st.write(f"Questions: {st.session_state.questions}")
    
    # Update session state
    st.session_state.analysis_results = {
        "correct_mcqs": correct_mcqs,
        "total_mcqs": total_mcqs,
        "correct_short": correct_short,
        "total_short": total_short,
        "score": total_score,
        "total": total_questions,
        "accuracy": accuracy,
        "time_taken": float(st.session_state.get('time_taken', 0)),
        "correct_answers": correct_answers,
        "incorrect_answers": incorrect_answers
    }
    # Update leaderboard
    if 'leaderboard' not in st.session_state:
        st.session_state.leaderboard = []
    st.session_state.leaderboard.append((
        float(st.session_state.time_taken),
        float(total_score)
    ))
    st.session_state.leaderboard.sort(key=lambda x: (-x[1], x[0]))

def display_analysis():
    """Display test results with enhanced visualization"""
    if not st.session_state.get('analysis_results'):
        st.error("No results available. Complete a test first.")
        return
    
    results = st.session_state.analysis_results
    
    st.title("📊 Test Results")
    
    # Summary Metrics with improved formatting
    col1, col2, col3 = st.columns(3)
    
    # Score
    score = max(0, min(results.get('score', 0), results.get('total', 1)))
    col1.metric("Score", f"{score:.1f}/{results.get('total', 1)}")
    
    # Accuracy
    accuracy = max(0, min(results.get('accuracy', 0), 100))
    col2.metric("Accuracy", f"{accuracy:.1f}%")
    
    # Time Taken
    time_taken = max(0, results.get('time_taken', 0))
    minutes = int(time_taken // 60)
    seconds = int(time_taken % 60)
    col3.metric("Time Taken", f"{minutes}m {seconds}s")
    
    # Performance Breakdown
    st.subheader("📈 Performance Breakdown")
    if results.get('total_mcqs', 0) > 0:
        mcq_accuracy = (results['correct_mcqs'] / results['total_mcqs']) * 100
        st.write(f"**MCQs:** {results['correct_mcqs']}/{results['total_mcqs']} ({mcq_accuracy:.1f}%)")
    
    if results.get('total_short', 0) > 0:
        short_accuracy = (results['correct_short'] / results['total_short']) * 100
        st.write(f"**Short Answers:** {results['correct_short']:.1f}/{results['total_short']} ({short_accuracy:.1f}%)")
    
    # Correct Answers
    if results.get('correct_answers'):
        st.subheader("✅ Correct Answers")
        for item in results['correct_answers']:
            with st.expander(f"{item['question']}"):
                st.write(f"**Your answer:** {item['user_answer']}")
                if item['type'] == "Short Answer":
                    st.write(f"**Keywords matched:** {item.get('matched_keywords', 0)}/{item.get('total_keywords', 1)}")
                    st.progress(item.get('score', 0))
                st.write(f"**Explanation:** {item.get('explanation', '')}")
    else:
        st.write("No correct answers")
    
    # Incorrect Answers
    if results.get('incorrect_answers'):
        st.subheader("❌ Incorrect Answers")
        for item in results['incorrect_answers']:
            with st.expander(f"{item['question']}"):
                st.write(f"**Your answer:** {item['user_answer']}")
                st.write(f"**Correct answer:** {item['correct_answer']}")
                if item['type'] == "Short Answer":
                    st.write(f"**Keywords matched:** {item.get('matched_keywords', 0)}/{item.get('total_keywords', 1)}")
                    st.progress(item.get('score', 0))
                st.write(f"**Explanation:** {item.get('explanation', '')}")
    else:
        st.write("No incorrect answers")
    
    # Leaderboard
    if st.session_state.get('leaderboard'):
        st.subheader("🏆 Leaderboard")
        for i, (time_val, score_val) in enumerate(st.session_state.leaderboard[:5], 1):
            minutes = int(time_val // 60)
            seconds = int(time_val % 60)
            st.write(f"{i}. Score: {score_val:.1f} | Time: {minutes}m {seconds}s")
    
    # Reset Button
    if st.button("🔄 Take New Test", type="primary"):
        st.session_state.update({
            "questions": [],
            "user_answers": {},
            "current_question_index": 0,
            "test_completed": False,
            "page": "upload"
        })
        st.rerun()