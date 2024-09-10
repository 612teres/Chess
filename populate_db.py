from app import app, db, Puzzle 

sample_puzzles = [
    {
        'fen': 'r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3',
        'solution': 'Nf6',
        'hint': 'Develop your knight to control the center.',
        'difficulty': 'easy'
    },
    {
        'fen': 'rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2',
        'solution': 'e6',
        'hint': "Challenge White's control of the center.", 
        'difficulty': 'medium'
    },
    {
        'fen': 'r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R b KQkq - 3 3',
        'solution': 'O-O',
        'hint': 'Protect your king and prepare for counter-play.',
        'difficulty': 'hard'
    }
]

def populate_puzzles():
    with app.app_context(): 
        for puzzle_data in sample_puzzles:
            new_puzzle = Puzzle(
                fen=puzzle_data['fen'],
                solution=puzzle_data['solution'],
                hint=puzzle_data['hint'],
                difficulty=puzzle_data['difficulty']
            )
            db.session.add(new_puzzle)

        db.session.commit()

if __name__ == '__main__':
    populate_puzzles()